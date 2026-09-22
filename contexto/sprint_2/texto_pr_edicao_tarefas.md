> Esta PR entrou em conflito de merge com a #47 (`ajustar-criacao-tarefas-admin`,
> já em `main`), que mexeu nos mesmos arquivos com uma regra parecida. O
> conflito foi resolvido priorizando a implementação da #47 onde as duas se
> sobrepunham; detalhes e a assimetria resultante entre `POST` e `PATCH`
> estão documentados em
> [`contexto/sprint_2/resumo_pr_edicao_tarefas.md`](contexto/sprint_2/resumo_pr_edicao_tarefas.md#merge-com-a-pr-47).

## Resumo

- Ajusta `PATCH /tarefas/{id_tarefa}` para editar peso, prazo e
  responsáveis, impedindo responsáveis duplicados ou de outra casa
  (`400` nos dois casos).
- Após o merge com a #47, `POST /tarefas/` passou a exigir `peso`, prazo
  futuro e ao menos um responsável, e valida que os responsáveis pertencem
  à casa — mas com um comportamento diferente do PATCH: deduplica
  responsáveis repetidos em vez de rejeitar, e retorna `422` (não `400`)
  para responsável de outra casa.
- Corrige um bug existente em `_montar_resposta` que chamava o dicionário
  da tarefa como função em vez de indexá-lo.
- Muda a penalidade por atraso na pontuação: em vez de uma taxa fixa por
  `tipo_de_penalidade`, a taxa diária agora é `100% / atraso_maximo` de
  cada tarefa (ex.: `atraso_maximo = 5` → -20%/dia; no 5º dia de atraso a
  tarefa perde 100% dos pontos e vira `nao_feito` automaticamente na
  próxima consulta).
- Remove a coluna `tipo_de_penalidade`, que ficou sem uso.
- Torna `pontuacao` obrigatória — corrige uma falha em que o crédito de
  pontos ao finalizar uma tarefa recebia `pontuacao = NULL`, já que esse
  campo nunca tinha sido exposto pela API.

## Migrations

- `docs/migrations/10.sql`: `atraso_maximo` `NOT NULL`/`CHECK > 0`; taxa de
  desconto do trigger de pontuação passa a usar `atraso_maximo`.
- `docs/migrations/11.sql`: remove `tipo_de_penalidade`.
- `docs/migrations/12.sql`: `pontuacao` `NOT NULL`.

**Ainda não aplicadas/testadas em um Supabase real** — rodar num ambiente
de teste antes do merge. Se houver tarefas já cadastradas sem
`atraso_maximo`/`pontuacao`, as migrations `NOT NULL` vão falhar ao aplicar
(precisa corrigir os dados antes).

## Detalhes

Contexto completo em
[`contexto/sprint_2/resumo_pr_edicao_tarefas.md`](contexto/sprint_2/resumo_pr_edicao_tarefas.md).

## Test plan

- [x] `pytest tests/ --ignore=tests/test_*_integracao.py` — 88 testes
      unitários aprovados (já incluindo os ajustes do merge com a #47).
- [ ] Rodar `test_tarefas_integracao.py` contra um Supabase de testes
      (não executado neste ambiente).
- [ ] Aplicar `docs/migrations/10.sql`, `11.sql` e `12.sql` no Supabase de
      testes/produção — ainda não aplicadas em nenhum ambiente real.

## Pendências conhecidas (fora do escopo deste PR)

- Assimetria `POST` (`422`, dedupe silencioso) vs `PATCH` (`400`, rejeita)
  para a mesma regra de responsáveis, criada ao resolver o conflito com a
  #47 — não unificada.
- `GET /casas/{id_casa}/moradores` não implementado.
- Nenhuma trava impede finalizar manualmente uma tarefa já além do
  `atraso_maximo` (resultado: `0` pontos, não erro).
- A transição para `nao_feito` só acontece quando a tarefa é consultada
  (não há cron/job agendado no projeto).
