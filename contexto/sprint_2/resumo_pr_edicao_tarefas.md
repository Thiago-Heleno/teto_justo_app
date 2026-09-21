# Resumo do PR — Edição/atribuição de tarefas e pontuação por atraso — Sprint 2

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

## 1. Edição e atribuição de tarefas

Documento completo: [edicao_atribuicao_tarefa.md](edicao_atribuicao_tarefa.md)

- `peso` (`Literal[1,2,3,4]`) exposto na API — obrigatório em `TarefaCriar`,
  opcional em `TarefaAtualizar` — mapeado para a coluna `dificuldade` no
  banco. Serve apenas para dividir o trabalho entre responsáveis, sem
  relação com pontuação.
- Prazo (`data_fim`) já era editável antes deste PR; nenhuma mudança
  necessária.
- Responsáveis (`usuarios_atribuidos`): nova validação
  `ServicoAutorizacaoCasa.garantir_responsaveis_da_casa`, chamada tanto na
  criação (`POST /tarefas/`) quanto na edição (`PATCH /tarefas/{id}`):
  - rejeita (`400`) UUID duplicado na lista;
  - rejeita (`400`) responsável que não pertence à casa da tarefa —
    considerando tanto os vínculos em `pertencer` quanto o dono da casa
    (`casa.fk_usuario_id`, que não fica em `pertencer`).
- Corrigido um bug preexistente em `_montar_resposta`
  (`services/tarefa.py`): `tarefa("dificuldade")` chamava o dicionário como
  função em vez de indexá-lo (`tarefa["dificuldade"]`).

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

- 83 testes unitários passando (mock do client Supabase, sem dependência de
  rede): `pytest tests/ --ignore=tests/test_*_integracao.py`.
- Testes de integração (`test_tarefas_integracao.py`, contra Supabase real)
  foram escritos/atualizados mas **não executados neste ambiente** — faltam
  credenciais de um Supabase de testes. Rodar antes do merge.

## Pendências conhecidas (não resolvidas neste PR)

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
  Supabase real.
