# Testes da entidade Casa

## Resumo

Foram adicionados testes unitários e de integração para a entidade `Casa` usando Pytest. Os testes unitários isolam o serviço, enquanto o teste de integração executa o CRUD pelas rotas reais da aplicação e utiliza o Supabase configurado para testes.

## Testes unitários

Arquivo: `src/backend/tests/test_servico_casa_unitario.py`

Os testes unitários verificam o comportamento de `ServicoCasa` sem acessar serviços externos. O cliente do Supabase é substituído por mocks nessa camada.

Casos cobertos:

- criação da casa e conversão da foto;
- criação sem foto e validação de Base64 inválido;
- erro `500` quando a inserção não retorna um registro;
- busca por ID e erro `404` para casa inexistente;
- validação do formato da foto retornada pelo banco;
- listagem e paginação;
- atualização parcial e conversão da nova foto;
- erro `400` para atualização vazia;
- erro `404` ao atualizar ou excluir uma casa inexistente;
- exclusão de uma casa existente.

## Teste de integração real

Arquivo: `src/backend/tests/test_casa_integracao.py`

O teste usa a aplicação FastAPI e o cliente Supabase configurado em `core.database`.

Fluxo preparado:

1. Cria um usuário temporário no Supabase de teste.
2. Cria uma casa por `POST /casas/`.
3. Busca a casa por `GET /casas/{id}`.
4. Verifica a casa na listagem por `GET /casas/`.
5. Atualiza a casa por `PATCH /casas/{id}`.
6. Exclui a casa por `DELETE /casas/{id}`.
7. Confirma que a busca posterior retorna `404`.
8. Remove no encerramento registros temporários restantes.

O teste valida as rotas FastAPI, schemas Pydantic, serviço de casa, cliente Supabase e persistência dos dados da casa, incluindo a foto.

## GitHub Actions

Workflow: `.github/workflows/backend-pytest.yml`

O workflow foi atualizado para incluir a integração de `Casa`.

1. Os testes sem serviços externos rodam em pushes e pull requests.
2. Os testes de integração rodam contra o Supabase de teste em pushes para a branch `main` ou por execução manual do workflow.

A integração recebe:

- `TEST_SUPABASE_URL` como `SUPABASE_URL`;
- `TEST_SUPABASE_KEY` como `SUPABASE_KEY`.

Os secrets devem apontar para um projeto Supabase exclusivo para testes.

## Validação realizada

Foram executados localmente com sucesso:

- 14 testes unitários de `Casa`;
- suíte sem dependências externas: `51 passed`;
- Ruff nos arquivos de teste: `All checks passed!`.

O teste de integração de `Casa` não foi executado localmente contra o Supabase, pois não foi confirmado que o `.env` local aponta exclusivamente para um banco de testes. A integração foi configurada no GitHub Actions para ser executada com o ambiente de teste definido pelos secrets.