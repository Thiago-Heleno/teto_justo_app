# Estado e consulta de tarefa — Sprint 1

## Objetivo

Adequar o estado das tarefas ao contrato textual do quadro e otimizar sua filtragem por casa e estado.

## Alterações

- `docs/migrations/08.sql` converte `tarefa.estado_atual` de `INT` para `VARCHAR(10)` e migra os códigos legados `0..3` para `pendente`, `atrasada`, `finalizado` e `nao_feito`, respectivamente.
- A migration adiciona a constraint `CK_Tarefa_estado_atual`, aceitando somente esses valores ASCII.
- O índice composto `IDX_Tarefa_Casa_Estado (fk_casa_id, estado_atual)` atende à consulta do quadro filtrada por casa e estado.

## Validação

- Revisão estática da sequência da migration e verificação de espaços em branco nos arquivos alterados.

## Pendência

- O contrato do backend ainda usa códigos inteiros para `estado_atual`; deverá ser atualizado antes de enviar novos estados à tabela migrada.
