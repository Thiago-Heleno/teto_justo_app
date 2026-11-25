# Regras da casa e multas (backend)

## Objetivo
Atender o contrato que `src/frontend/src/services/regras-casa-api.ts` já consome em `/regras-casa/...`.
Entrega em duas partes: regras (feita) e multas (pendente).

## Parte 1: regras (feita)
- `docs/migrations/39.sql`: tabela `regra_casa` (FK para `casa` com `ON DELETE CASCADE`, `valor_multa_centavos` > 0, índice em `fk_casa_id`).
- `src/backend/schemas/regra_casa.py`, `services/regra_casa.py`, `routers/regra_casa.py`; router registrado em `main.py`.
- Rotas: `POST /regras-casa/`, `GET /regras-casa/casa/{id_casa}`, `PATCH /regras-casa/{id_regra}`, `DELETE /regras-casa/{id_regra}`.
- Permissões: listar para administrador ou morador ativo; criar, editar e excluir só para o administrador.

## Decisões
- `valor_multa_centavos` entre 1 e 2147483647 (limite do `INT`, igual ao frontend).
- `descricao` vazia vira `null`; `titulo`, `valor_multa_centavos` e `ativa` não aceitam `null` no PATCH; PATCH sem campos retorna 422.
- Lógica em Python, sem funções no banco.

## Validação
- `pytest tests/test_regra_casa_unitario.py tests/test_lista_unitario.py` (pasta `src/backend`): 17 passaram (banco em memória, são testes de unidade).
- `ruff check` e `ruff format --check` em `src/backend`: sem pendências.
- Migration 39 não foi aplicada em nenhum banco; não há teste de integração.

## Pendências
- Parte 2: tabela `multa_casa` (migration 40) e rotas de multas: `GET /regras-casa/casa/{id_casa}/multas`, `POST /regras-casa/multas`, `POST|DELETE /regras-casa/multas/{id}/pagar`, `DELETE /regras-casa/multas/{id}`. Declarar as rotas `/multas` antes das `/{id_regra}`.
- Regras da parte 2: só administrador aplica, paga e exclui; a regra deve ser da mesma casa e estar ativa; o multado deve ser o administrador ou morador ativo; `valor_centavos` e `titulo_regra` são copiados da regra na criação.
- Teste de integração contra o Supabase de teste.
