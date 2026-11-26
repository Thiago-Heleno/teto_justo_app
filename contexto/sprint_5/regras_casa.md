# Regras da casa e multas (backend)

## Objetivo
Atender o contrato que `src/frontend/src/services/regras-casa-api.ts` já consome em `/regras-casa/...`.
Entregue em duas partes: regras e multas.

## Arquivos
- `docs/migrations/39.sql`: tabela `regra_casa`.
- `docs/migrations/41.sql`: tabela `multa_casa` (a 40 é da roleta).
- `src/backend/schemas/regra_casa.py`, `services/regra_casa.py`, `routers/regra_casa.py`; router registrado em `main.py`.
- `src/backend/tests/test_regra_casa_unitario.py`.

## Rotas
- Regras: `POST /regras-casa/`, `GET /regras-casa/casa/{id_casa}`, `PATCH|DELETE /regras-casa/{id_regra}`.
- Multas: `GET /regras-casa/casa/{id_casa}/multas` (mais recentes primeiro), `POST /regras-casa/multas`, `POST|DELETE /regras-casa/multas/{id_multa}/pagar`, `DELETE /regras-casa/multas/{id_multa}`.
- Listar: administrador ou morador ativo. As demais operações: só o administrador.

## Decisões
- `valor_multa_centavos` entre 1 e 2147483647 (limite do `INT`, igual ao frontend).
- `descricao` e `observacao` vazias viram `null`; `titulo`, `valor_multa_centavos` e `ativa` não aceitam `null` no PATCH; PATCH sem campos retorna 422.
- A multa exige regra da mesma casa e ativa; o multado é o administrador ou um morador ativo. `titulo_regra` e `valor_centavos` são copiados da regra na criação.
- Excluir regra com multas retorna 409, para preservar o histórico (a tela orienta pausar a regra). No banco, `fk_regra_id` não tem `CASCADE`; excluir a casa ainda apaga regras e multas.
- As chaves para `usuario` usam `ON DELETE RESTRICT`, como `item_compra`.
- Lógica em Python, sem funções no banco.

## Validação
- `pytest tests/test_regra_casa_unitario.py` (pasta `src/backend`): 16 passaram (banco em memória, são testes de unidade).
- `pytest tests -k unitario`: 840 passaram, 37 fora da seleção.
- `ruff check` em `src/backend` e `ruff format --check` nos arquivos da funcionalidade: sem pendências.

## Pendências
- Aplicar as migrations 39 e 41 no banco; não foram aplicadas por esta implementação.
- Não há teste de integração contra o Supabase de teste, e a tela não foi exercitada contra o backend.
