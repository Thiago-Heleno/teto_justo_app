## Resumo

- Ajusta `PATCH /tarefas/{id_tarefa}` para editar peso, prazo e
  responsáveis, impedindo responsáveis duplicados ou de outra casa. A mesma
  validação de responsáveis passou a valer também na criação
  (`POST /tarefas/`).
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

- [x] `pytest tests/ --ignore=tests/test_*_integracao.py` — 83 testes
      unitários aprovados.
- [ ] Rodar `test_tarefas_integracao.py` contra um Supabase de testes
      (não executado neste ambiente).
- [ ] Aplicar `docs/migrations/10.sql`, `11.sql` e `12.sql` no Supabase de
      testes antes do merge.

## Pendências conhecidas (fora do escopo deste PR)

- `GET /casas/{id_casa}/moradores` não implementado.
- Nenhuma trava impede finalizar manualmente uma tarefa já além do
  `atraso_maximo` (resultado: `0` pontos, não erro).
- A transição para `nao_feito` só acontece quando a tarefa é consultada
  (não há cron/job agendado no projeto).
