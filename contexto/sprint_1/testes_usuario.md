# Testes da entidade Usuário

## Resumo

Foram adicionados testes unitários e de integração para a entidade `Usuario` usando Pytest. Os testes unitários isolam o serviço com um banco falso, enquanto o teste de integração executa o CRUD pelas rotas reais da aplicação, também contra um banco falso em memória injetado via `dependency_overrides` do FastAPI — diferente da entidade `Sessao`, cujo teste de integração roda contra um Supabase de teste real.

## Testes unitários

Arquivo: `src/backend/tests/test_servico_usuario_unitario.py`

Os testes unitários verificam o comportamento de `ServicoUsuario` sem acessar serviços externos. O cliente do Supabase é substituído por um `BancoMemoria` (dicionário em memória que imita a interface fluente `table().select().eq().insert().update().delete().execute()`) ou por `MagicMock`, conforme o caso.

Casos cobertos:

- geração de hash de senha com `bcrypt` (o hash gerado é diferente da senha original);
- erro `400` na criação quando já existe um usuário com o mesmo e-mail;
- busca por ID e erro `404` para usuário inexistente;
- atualização somente dos campos enviados, preservando os demais;
- erro `400` para atualização sem nenhum campo preenchido;
- erro `404` ao atualizar ou excluir um usuário inexistente;
- exclusão de um usuário existente, confirmando a remoção do banco.

## Teste de integração

Arquivo: `src/backend/tests/test_usuarios_crud.py`

Diferente do teste de `Sessao`, este teste não usa um Supabase de teste real. Ele sobe uma aplicação FastAPI isolada, registrando apenas o router de usuário, e substitui a dependência `get_supabase` por um `BancoMemoria` novo a cada teste (`setUp`/`tearDown`), via `TestClient`.

Fluxo executado no CRUD completo:

1. Cria um usuário por `POST /usuarios/`.
2. Confirma que a resposta não expõe `senha` nem `senha_hash`.
3. Busca o usuário por `GET /usuarios/{id}`.
4. Atualiza o nome por `PATCH /usuarios/{id}`.
5. Exclui o usuário por `DELETE /usuarios/{id}`.
6. Confirma que a busca posterior retorna `404`.

Também são cobertos, em testes separados:

- rejeição de e-mail duplicado na criação (`400`);
- payload inválido na criação (`422`);
- id malformado na busca (`422`);
- busca, atualização e exclusão de um id inexistente (`404`);
- atualização sem nenhum campo enviado (`400`).

Esse teste valida as rotas FastAPI, os schemas Pydantic e o serviço de usuário, mas não valida a tabela, as colunas ou constraints reais do banco, já que não fala com o Supabase.

## Dependências de teste

Os testes usam o mesmo `src/backend/requirements-dev.txt` já criado para os testes de `Sessao`, com Pytest e HTTPX.

## GitHub Actions

Workflow: `.github/workflows/backend-pytest.yml`

Como o teste de `Usuario` não depende do Supabase, ele roda junto com os demais testes sem serviços externos, em todo push e pull request — não está na lista de `--ignore` nem na etapa exclusiva de integração real (que hoje cobre só `Sessao` e `Tarefa`).

## Validação realizada

Os testes de `Usuario` foram executados localmente com sucesso: `12 passed` (`test_servico_usuario_unitario.py` + `test_usuarios_crud.py`).
