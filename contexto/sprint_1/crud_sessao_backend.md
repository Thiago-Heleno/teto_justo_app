# CRUD de Sessão (Backend) — Sprint 1

## O que foi feito

Implementado o CRUD da entidade `Sessao` no backend com FastAPI e Supabase. A entidade representa os tokens de login de um usuário.

O diagrama ER define que um usuário pode ter nenhuma ou várias sessões e que cada sessão pertence a exatamente um usuário. As migrations confirmam os campos `id` (UUID), `token`, `criado_em`, `expira_em` e `fk_usuario_id`; a exclusão de um usuário remove suas sessões em cascata.

## Estrutura adicionada

- `schemas/sessao.py`: contratos de criação, atualização e resposta da API.
- `services/sessao.py`: acesso à tabela `sessao` e tratamento dos erros de negócio.
- `routers/sessao.py`: definição das rotas HTTP.
- `main.py`: registro do router de sessões na aplicação.

O campo `criado_em` não é enviado na criação: seu valor é gerado pelo default `CURRENT_TIMESTAMP` definido na migration. Depois de criada, uma sessão permite alterar apenas o token e a data de expiração; o usuário vinculado é preservado.

## Endpoints disponíveis

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/sessoes/` | Cria uma sessão com token, expiração e usuário vinculado. |
| `GET` | `/sessoes/` | Lista sessões, com paginação por `inicio` e `limite`. |
| `GET` | `/sessoes/{id_sessao}` | Busca uma sessão por UUID. |
| `PATCH` | `/sessoes/{id_sessao}` | Atualiza token e/ou data de expiração. |
| `DELETE` | `/sessoes/{id_sessao}` | Remove a sessão, revogando o token. |

## Respostas de erro

- UUID ou payload inválido: `422`.
- Sessão inexistente: `404`.
- Atualização sem campos: `400`.
- Falha ao inserir uma sessão: `500`.

## Testes

Adicionado `tests/test_sessoes_crud.py`, cobrindo criação, busca, listagem, atualização, exclusão e validações da API usando um banco em memória.
