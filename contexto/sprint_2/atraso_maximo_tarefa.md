# Atraso máximo de tarefa — Sprint 2

## Objetivo

Registrar o atraso máximo permitido para a conclusão de uma tarefa.

> **Atualizado em 21/09/2026** — a coluna passou a ser obrigatória, positiva,
> exposta na API e usada tanto no cálculo de pontuação quanto para marcar a
> tarefa como `nao_feito` automaticamente. Ver
> [edicao_atraso_pontuacao_tarefa.md](edicao_atraso_pontuacao_tarefa.md).

## Alteração

- `docs/migrations/06.sql` adiciona a coluna `atraso_maximo INT` à tabela `tarefa`.
- `docs/migrations/10.sql` torna a coluna `NOT NULL` e adiciona a constraint `CK_Tarefa_atraso_maximo CHECK (atraso_maximo > 0)`.
- `schemas/tarefa.py` expõe `atraso_maximo` como campo obrigatório em `TarefaCriar` e `TarefaResposta`, e opcional em `TarefaAtualizar`.

## Limitação

- Nenhuma pendência conhecida no contrato de `atraso_maximo`. A migration
  original (`06.sql`) permitia valor nulo; isso foi corrigido em `10.sql`,
  seguro porque não havia tarefas registradas no banco até esta mudança.
