# Lista de compras (backend)

## Objetivo
Expor o CRUD de listas de compras e de itens, conforme as migrations `docs/migrations/36.sql` a `38.sql` (`lista_compra`, `item_compra` e índices).

## Arquivos
- `src/backend/routers/lista.py`: rotas sob `/lista`.
- `src/backend/services/lista.py`: `ServicoLista`, com a lógica e a autorização.
- `src/backend/main.py`: registro do router.
- Schemas reaproveitados, sem alteração: `schemas/lista.py` e `schemas/item.py`.

## Rotas
- Lista: `POST /lista/`, `GET /lista/casa/{id_casa}`, `PATCH /lista/{id_lista}`, `DELETE /lista/{id_lista}`.
- Item: `POST /lista/itens`, `GET /lista/{id_lista}/itens`, `PATCH /lista/itens/{id_item}`, `DELETE /lista/itens/{id_item}`.
- Compra: `POST /lista/itens/{id_item}/comprado` marca; `DELETE` na mesma rota desmarca.

## Decisões
- Administrador e moradores ativos fazem tudo (`garantir_acesso`). Só o administrador apaga uma lista (`garantir_administrador_da_casa`).
- O criador do item vem do usuário autenticado, não do corpo da requisição.
- Ao marcar como comprado, grava `fk_usuario_comprador_id` e `comprado_em` (UTC). Ao desmarcar, limpa os dois campos.
- `PATCH` de item sem campos retorna 422.
- Itens são apagados junto com a lista pelo `ON DELETE CASCADE` da migration.

## Validação
- O app importa e o OpenAPI lista as 7 rotas de path. Nada além disso foi executado.

## Pendências
- Sem testes automatizados.
- Não há rota para buscar lista ou item individual por ID.
