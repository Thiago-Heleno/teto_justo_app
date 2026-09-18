# Pontuação e penalidade de tarefa — Sprint 2

## Objetivo

Adicionar atributos de dificuldade e penalidade às tarefas e registrar eventos de pontuação.

## Alterações

- `docs/migrations/07.sql` adiciona a `tarefa` as colunas `dificuldade`, `tipo_de_penalidade` e `concluida_em`.
- As constraints aceitam os valores `1` a `4` para dificuldade e tipo de penalidade, e `10`, `20`, `30` ou `40` para pontuação.
- A tabela `score_event` registra a pontuação por usuário, casa e tarefa, com unicidade por usuário e tarefa e chaves estrangeiras para as entidades relacionadas.
