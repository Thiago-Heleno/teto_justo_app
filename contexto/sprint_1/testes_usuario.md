# Testes da entidade Usuário

## Resumo

Foram adicionados testes unitários e de integração para a entidade `Usuario` usando Pytest. Os testes unitários isolam o serviço com um banco falso, enquanto o teste de integração executa o CRUD pelas rotas reais da aplicação e persiste os dados em um projeto Supabase exclusivo para testes — mesmo padrão adotado pela entidade `Sessao`.

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

## Teste de integração real

Arquivo: `src/backend/tests/test_usuarios_integracao.py`

O teste sobe a aplicação FastAPI completa (`main.app`) com um `TestClient` e usa o cliente Supabase real configurado em `core.database`. Não há mais banco falso em memória para esse fluxo.

Fluxo executado no CRUD completo:

1. Cria um usuário por `POST /usuarios/` com e-mail único gerado por fixture (`usuario_payload`).
2. Confirma que a resposta não expõe `senha` nem `senha_hash`.
3. Busca o usuário por `GET /usuarios/{id}`.
4. Atualiza o nome por `PATCH /usuarios/{id}`.
5. Exclui o usuário por `DELETE /usuarios/{id}`.
6. Confirma que a busca posterior retorna `404`.
7. A fixture `limpar_usuario` remove no encerramento qualquer usuário criado durante o teste diretamente no Supabase.

Também são cobertos, em testes separados:

- rejeição de e-mail duplicado na criação (`400`);
- payload inválido na criação (`422`);
- id malformado na busca (`422`);
- busca, atualização e exclusão de um id inexistente (`404`);
- atualização sem nenhum campo enviado (`400`).

Esse teste valida de fato:

- as rotas FastAPI;
- os schemas Pydantic;
- o serviço de usuário;
- o cliente Supabase;
- a tabela e as colunas reais;
- a regra de e-mail único aplicada pelo banco/serviço.

## Dependências de teste

Os testes usam o mesmo `src/backend/requirements-dev.txt` já criado para os testes de `Sessao`, com Pytest e HTTPX.

## GitHub Actions

Workflow: `.github/workflows/backend-pytest.yml`

O workflow possui duas etapas de teste:

1. Os testes que não dependem de serviços externos rodam em pushes e pull requests. `test_usuarios_integracao.py` está na lista de `--ignore` dessa etapa, junto com as integrações reais de `Sessao`, `Tarefa`, `Casa` e `Pertencer`.
2. A integração real de `Usuario` (e das demais entidades citadas) roda em pushes para a branch `main` ou por execução manual do workflow, usando `TEST_SUPABASE_URL`/`TEST_SUPABASE_KEY` como `SUPABASE_URL`/`SUPABASE_KEY`.

## Validação realizada

A suíte unitária de `Usuario` (`test_servico_usuario_unitario.py`) foi executada localmente com sucesso. O teste de integração real (`test_usuarios_integracao.py`) não foi executado localmente, seguindo o mesmo cuidado adotado para `Sessao`: evitar alterações em um banco cuja finalidade não estava confirmada. Sua execução ocorre no GitHub Actions usando o ambiente configurado pelos secrets.
