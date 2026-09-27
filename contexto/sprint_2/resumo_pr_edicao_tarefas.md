# Resumo do PR — Edição/atribuição de tarefas e pontuação por atraso — Sprint 2

> Este resumo descreve o estado do PR naquela entrega. Para o contrato e a
> pontuação posteriores, consulte
> [alinhamento_tarefas_pontuacao.md](alinhamento_tarefas_pontuacao.md) e
> [documentacao_sistema_pontuacao.md](documentacao_sistema_pontuacao.md).

Consolida em um único lugar tudo que foi feito neste PR. Os detalhes de cada
parte continuam nos documentos específicos, linkados abaixo.

## Origem

Duas tarefas do backlog:

- Backend - Ajustar edição e atribuição de tarefas: ajustar
  `PATCH /tarefas/{id_tarefa}` para editar peso, prazo e responsáveis;
  impedir responsáveis duplicados ou de outra casa.
- Durante a implementação, uma conversa sobre a pontuação por atraso levou a
  três mudanças adicionais, encadeadas: penalidade proporcional ao
  `atraso_maximo`, remoção de `tipo_de_penalidade` (ficou sem uso) e
  obrigatoriedade de `pontuacao` (campo que nunca tinha sido exposto na API
  e travava o crédito de pontos).

`GET /casas/{id_casa}/moradores` (a outra tarefa do backlog original) **não
foi feito neste PR** — ver Pendências.

Durante o desenvolvimento, a PR #47 (`ajustar-criacao-tarefas-admin`,
já mergeada em `main` antes desta PR) implementou, em paralelo e sem
conhecimento desta branch, uma validação parecida para `POST /tarefas/`.
Isso gerou um conflito de merge real (não só textual) entre as duas
implementações — ver seção "Merge com a PR #47" abaixo para como foi
resolvido.

## 1. Edição e atribuição de tarefas

Documento completo: [edicao_atribuicao_tarefa.md](edicao_atribuicao_tarefa.md)

- `peso` (`int`, de 1 a 4) exposto na API — obrigatório em `TarefaCriar`,
  opcional em `TarefaAtualizar` — mapeado para a coluna `dificuldade` no
  banco. Serve apenas para dividir o trabalho entre responsáveis, sem
  relação com pontuação.
- Prazo (`data_fim`): já era editável antes deste PR. A PR #47 acrescentou
  uma validação nova (mantida no merge): `data_fim` precisa estar no
  futuro tanto na criação quanto — via herança do mesmo validador — em
  qualquer edição que o informe.
- `usuarios_atribuidos` passou a ser **obrigatório na criação** (mínimo 1
  responsável) — regra da PR #47, mantida no merge. Na edição continua
  opcional (PATCH edita só o que foi enviado).
- Responsáveis — **duas implementações diferentes coexistem hoje**, uma
  para cada verbo, por causa do merge (ver seção abaixo):
  - **`POST /tarefas/`** (versão da PR #47, mantida como está): verifica
    quem pertence à casa via `pertencer` filtrado; responsável duplicado
    na lista é **deduplicado silenciosamente** (não gera erro); responsável
    que não pertence à casa retorna **`422`**.
  - **`PATCH /tarefas/{id}`** (desta branch): `ServicoAutorizacaoCasa
    .garantir_responsaveis_da_casa` **rejeita** (`400`) UUID duplicado na
    lista e responsável que não pertence à casa — considerando tanto os
    vínculos em `pertencer` quanto o dono da casa (`casa.fk_usuario_id`,
    que não fica em `pertencer`).
- Corrigido um bug preexistente em `_montar_resposta`
  (`services/tarefa.py`): `tarefa("dificuldade")` chamava o dicionário como
  função em vez de indexá-lo (`tarefa["dificuldade"]`).

## Merge com a PR #47

A PR #47 (`Ajusta regras de criação de tarefas`, commit `81b2afb`, já em
`main`) mexeu nos mesmos arquivos por um motivo parecido — exigir peso,
prazo futuro e responsáveis vinculados à casa na criação — mas de forma
independente desta branch. Resultado: conflito real em
`schemas/tarefa.py`, `services/autorizacao.py`, `services/tarefa.py` e
`test_servico_tarefa_unitario.py` ao atualizar esta branch com `main`.

Critério usado para resolver (a pedido de quem revisou): nas partes em que
as duas implementações faziam a mesma coisa, manter a versão da PR #47;
adicionar só o que era exclusivo desta branch por cima.

- **Mantido da PR #47**: `peso: int = Field(gt=0, le=4)` (em vez do
  `Literal[1,2,3,4]` que esta branch tinha), `usuarios_atribuidos`
  obrigatório com mínimo 1, validador de prazo futuro, `garantir_
  administrador_da_casa` passando a retornar o id do administrador, e toda
  a checagem de responsáveis do `POST /tarefas/` (inline, `.in_()` no
  `pertencer`, dedupe silencioso, `422`).
- **Mantido desta branch (exclusivo, PR #47 não tinha)**: `pontuacao`,
  `atraso_maximo`, a transição automática para `nao_feito`, a remoção de
  `tipo_de_penalidade`, o bug fix de `_montar_resposta`, e a validação de
  responsáveis do `PATCH` (`garantir_responsaveis_da_casa`, `400`).
- Testes ajustados para o comportamento final: removido um teste desta
  branch que duplicava o que a PR #47 já testava; os testes que esperavam
  `400`/duplicado-rejeitado no `POST` foram corrigidos para `422`/dedupe
  silencioso, que é o comportamento real herdado da PR #47.
- Commit de merge: `425fbc4` na branch `patch-em-tarefas`.

**Pendência gerada pelo próprio merge**: a assimetria `POST` (`422`,
dedupe) vs `PATCH` (`400`, rejeita) para a mesma regra de negócio não foi
unificada — ver Pendências.

## 2. Penalidade de pontuação proporcional ao atraso máximo

Documento completo:
[edicao_atraso_pontuacao_tarefa.md](edicao_atraso_pontuacao_tarefa.md)

- A taxa diária de desconto no crédito de pontos deixou de ser fixa por
  `tipo_de_penalidade` (10/20/30/40%/dia) e passou a ser `100% /
  atraso_maximo`, variável por tarefa (ex.: `atraso_maximo = 5` → -20%/dia;
  no 5º dia de atraso a perda chega a 100%).
- `atraso_maximo` passou a ser obrigatório e positivo, tanto no banco
  (`NOT NULL` + `CHECK > 0`) quanto na API (`TarefaCriar`).
- Sem nenhum job/cron no projeto, a tarefa passa a virar `nao_feito`
  sozinha (sem crédito de pontos) na primeira vez que é **consultada**
  depois de ultrapassar `atraso_maximo` — não há necessidade de
  infraestrutura nova, mas também não há garantia de que o estado no banco
  reflita a realidade sem nenhuma consulta prévia.

## 3. Remoção de `tipo_de_penalidade`

Detalhes também em
[edicao_atraso_pontuacao_tarefa.md](edicao_atraso_pontuacao_tarefa.md) e
[pontuacao_tarefa.md](pontuacao_tarefa.md).

- Coluna e constraint removidas do banco: ficaram sem uso assim que a taxa
  passou a vir de `atraso_maximo`, e nunca tinham sido expostas na API.

## 4. `pontuacao` obrigatória

Detalhes em
[edicao_atraso_pontuacao_tarefa.md](edicao_atraso_pontuacao_tarefa.md).

- `pontuacao` (10/20/30/40, a base de pontos da tarefa — independente de
  `peso`) nunca tinha sido exposta na API. Isso significava que o trigger
  de crédito de pontos recebia `pontuacao = NULL` ao finalizar qualquer
  tarefa, o que deveria falhar (`score_event.pontuacao` é `NOT NULL`).
- Passou a ser campo obrigatório em `TarefaCriar`/`TarefaResposta`
  (`PontuacaoTarefa = Literal[10, 20, 30, 40]`) e a coluna no banco virou
  `NOT NULL`.

## Migrations novas

| Arquivo | O que faz |
| --- | --- |
| [`docs/migrations/10.sql`](../../docs/migrations/10.sql) | `atraso_maximo` `NOT NULL` + `CHECK > 0`; reescreve o trigger de crédito de pontos para usar `100.0 / atraso_maximo` como taxa diária. |
| [`docs/migrations/11.sql`](../../docs/migrations/11.sql) | Remove a coluna `tipo_de_penalidade` e sua constraint. |
| [`docs/migrations/12.sql`](../../docs/migrations/12.sql) | `pontuacao` `NOT NULL`. |

**Nenhuma das três foi aplicada nem testada contra um Supabase real** —
precisa rodar num ambiente de teste antes do merge. Se houver alguma tarefa
já cadastrada sem `atraso_maximo`/`pontuacao` preenchidos, as migrations
`NOT NULL` vão falhar ao aplicar (comportamento seguro: falha alto e claro,
em vez de deixar dado inconsistente) — nesse caso, os dados precisam ser
corrigidos manualmente antes.

## Arquivos alterados

```
contexto/sprint_2/atraso_maximo_tarefa.md          (atualizado)
contexto/sprint_2/credito_pontos_tarefa.md         (atualizado)
contexto/sprint_2/pontuacao_tarefa.md              (atualizado)
contexto/sprint_2/edicao_atribuicao_tarefa.md      (novo)
contexto/sprint_2/edicao_atraso_pontuacao_tarefa.md (novo)
contexto/sprint_2/resumo_pr_edicao_tarefas.md      (novo, este arquivo)
contexto/sprint_2/texto_pr_edicao_tarefas.md       (novo)
contexto/sprint_2/criacao_tarefas_admin.md         (novo, veio da PR #47 — não escrito nesta branch)
docs/migrations/10.sql                             (novo)
docs/migrations/11.sql                             (novo)
docs/migrations/12.sql                             (novo)
src/backend/schemas/tarefa.py
src/backend/services/autorizacao.py
src/backend/services/tarefa.py
src/backend/tests/test_servico_tarefa_unitario.py
src/backend/tests/test_tarefas_integracao.py
```

## Testes

- 88 testes unitários passando (mock do client Supabase, sem dependência de
  rede): `pytest tests/ --ignore=tests/test_*_integracao.py`.
- Testes de integração (`test_tarefas_integracao.py`, contra Supabase real)
  foram escritos/atualizados mas **não executados neste ambiente** — faltam
  credenciais de um Supabase de testes.

## Status

Mergeado em `main` via PR #49 (commit `bae732e`), com a branch
`patch-em-tarefas` já reconciliada com a PR #47. As pendências abaixo
continuam abertas em `main` depois do merge — nada disto bloqueou o merge,
mas seguem como trabalho futuro.

## Pendências conhecidas (não resolvidas neste PR)

- **Assimetria `POST` vs `PATCH` para a mesma regra de negócio**, criada
  pela resolução do merge com a PR #47: `POST /tarefas/` deduplica
  responsáveis repetidos silenciosamente e retorna `422` para responsável
  de outra casa; `PATCH /tarefas/{id}` rejeita (`400`) os dois casos. Não
  foi unificado a pedido de quem revisou o merge (priorizar a versão já
  existente na PR #47 sem alterá-la).
- `GET /casas/{id_casa}/moradores` não foi implementado (outra tarefa do
  backlog).
- Nenhuma trava impede finalizar manualmente (`PATCH
  estado_atual=finalizado`) uma tarefa já além do `atraso_maximo`; o
  resultado é `0` pontos creditados, não um erro.
- A transição para `nao_feito` só acontece quando a tarefa é consultada
  (sem cron/job agendado no projeto).
- Listar tarefas pode disparar uma consulta extra ao banco por tarefa
  vencida na lista (checagem de sincronização por item) — sem impacto
  perceptível no tamanho atual do app.
- Migrations `10.sql`, `11.sql` e `12.sql` não aplicadas/testadas contra
  Supabase real — precisa rodar num ambiente de teste/produção antes de
  depender do novo cálculo de pontuação.
