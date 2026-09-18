# Estado e consulta de tarefa — Sprint 1

## Objetivo

Adequar o estado das tarefas ao contrato textual do quadro e otimizar sua filtragem por casa e estado.

## Alterações

- `docs/migrations/08.sql` converte `tarefa.estado_atual` de `INT` para `VARCHAR(10)` e migra os códigos legados `0..3` para `pendente`, `atrasada`, `finalizado` e `nao_feito`, respectivamente.
- A migration adiciona a constraint `CK_Tarefa_estado_atual`, aceitando somente esses valores ASCII.
- O índice composto `IDX_Tarefa_Casa_Estado (fk_casa_id, estado_atual)` atende à consulta do quadro filtrada por casa e estado.

## Validação

- O contrato do backend foi alinhado aos estados textuais da migration.
- Os schemas de criação, atualização e resposta aceitam somente
  `pendente`, `atrasada`, `finalizado` e `nao_feito`.
- Os testes unitários rejeitam tanto os códigos numéricos legados quanto
  estados textuais fora do contrato.
- A suíte unitária do workflow foi executada com 65 testes aprovados.
- A suíte completa teve 74 testes coletados sem erros de importação.
- A compilação de `schemas`, `services` e `tests` foi executada sem erros.

## Pendência

- Nenhuma pendência conhecida no contrato de `estado_atual`. Os testes de
  integração com o Supabase não foram executados localmente.
