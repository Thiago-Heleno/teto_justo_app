# Listagem de tarefas com filtros

## Objetivo

Adicionar a listagem de tarefas por casa com filtros de estado, responsável e prazo.

## Alterações

- A rota existente `GET /tarefas/casa/{id_casa}` passou a aceitar os filtros.
- A rota de casas não foi duplicada; o contrato existente foi preservado.
- Os filtros `estado`, `responsavel` e `prazo` são aplicados sobre tarefas da casa, incluindo responsáveis relacionados e a sincronização automática de atraso já existente.

## Validação

- 26 testes unitários de tarefas e 90 testes unitários do backend passaram.
- A verificação de sintaxe e `git diff --check` passaram.
- O lint com Ruff não foi executado porque o pacote não está instalado no ambiente.
- Os testes de integração dependem das credenciais do Supabase e não foram executados.
