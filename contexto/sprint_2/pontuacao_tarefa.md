# Pontuação e penalidade de tarefa — Sprint 2

## Objetivo

Adicionar atributos de dificuldade e penalidade às tarefas e registrar eventos de pontuação.

> **Atualizado em 21/09/2026** — `tipo_de_penalidade` foi removido em
> `docs/migrations/11.sql`, substituído pela taxa de desconto baseada em
> `atraso_maximo`. Ver
> [edicao_atraso_pontuacao_tarefa.md](edicao_atraso_pontuacao_tarefa.md).

## Alterações

- `docs/migrations/07.sql` adiciona a `tarefa` as colunas `dificuldade`, `tipo_de_penalidade` e `concluida_em`.
- As constraints aceitam os valores `1` a `4` para dificuldade e tipo de penalidade, e `10`, `20`, `30` ou `40` para pontuação.
- A tabela `score_event` registra a pontuação por usuário, casa e tarefa, com unicidade por usuário e tarefa e chaves estrangeiras para as entidades relacionadas.
- `docs/migrations/11.sql` remove `tipo_de_penalidade` e sua constraint: a coluna nunca foi exposta pela API e deixou de ser lida pelo trigger de crédito de pontos assim que `atraso_maximo` passou a definir a taxa diária de desconto.
