# Testes do CRUD da casa por cargo

## Objetivo

Cobrir com testes unitários e de integração (Supabase real) o comportamento de cada operação da casa para os três perfis de acesso, incluindo os casos de `403`:

- **administrador**: dono da casa (`casa.fk_usuario_id`);
- **morador**: usuário comum com vínculo ativo em `pertencer`;
- **forasteiro**: usuário sem vínculo ativo com a casa.

## Alterações

### Unitário do router

Arquivo: `src/backend/tests/test_contrato_casa_router_unitario.py`

- `test_operacoes_da_casa_por_cargo`: matriz cargo × operação (`GET /casas/{id}`, `GET /casas/{id}/moradores`, `PATCH`, `DELETE`) com o status esperado. Nos casos `403`, também verifica que a tabela `casa` não foi alterada.
- `test_listagem_inclui_casas_de_administrador_e_morador_mas_nao_do_forasteiro`.
- Os cargos reutilizam a fixture `ambiente`: `casas[1]` (usuário é dono), `casas[2]` (usuário é morador) e `casas[3]` (vínculo inativo, ou seja, forasteiro).

### Integração real (Supabase)

Arquivo: `src/backend/tests/test_casa_integracao.py`

- Fixture `cenario_cargos`: cria uma casa pela API com o administrador, vincula o morador em `pertencer` e mantém um terceiro usuário sem vínculo. Remove vínculo e casa no encerramento.
- Leitura (casa, moradores e listagem): `200` para administrador e morador, `403` para forasteiro.
- `PATCH` e `DELETE`: `403` para morador e forasteiro, com conferência de que o nome da casa no banco não mudou.
- Administrador edita e exclui uma casa que tem morador vinculado.

## Decisões

- Os três cargos são derivados dos dados já existentes; nenhuma mudança em código de produção.
- A rota de convites (`POST /casas/{id}/convites`) ficou fora da integração porque depende de `CASA_CONVITE_SECRET`; o `403` dela já é coberto no teste unitário do router.

## Validações

- `ruff check tests`: sem erros após as correções.
- Suíte unitária no CI antes da correção: 343 passaram e 12 falharam, por `ID_POR_CARGO` com chaves e números errados. A correção foi aplicada, mas a suíte completa não foi reexecutada localmente (falta o módulo `redis` no Python local).
- Testes de integração: não executados localmente; dependem do Supabase de teste no CI.

## Limitações

- A exclusão de casa com morador vinculado só passa se o banco remover o vínculo junto (cascade em `pertencer`); se falhar com `409`, o schema precisa ser revisado.
- O unitário `test_edicao_e_exclusao_sao_reservadas_ao_proprietario` passou a ser redundante com a nova matriz.
