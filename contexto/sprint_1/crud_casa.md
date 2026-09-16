# CRUD de Casa (Backend) — Sprint 1

## Resumo

Foi implementado o CRUD da entidade `Casa` no backend com FastAPI e Supabase.
Uma casa representa a residência ou o grupo no qual usuários e tarefas são
organizados e mantém o vínculo com seu proprietário por `fk_usuario_id`.

Os nomes dos campos estão em português e correspondem diretamente às colunas
utilizadas no banco. O serviço não utiliza `FIELD_MAP`.

## Estrutura implementada

### `src/backend/schemas/casa.py`

Foram definidos três contratos Pydantic:

- `CasaCriar`: recebe `nome`, `endereco`, `foto` opcional e
  `fk_usuario_id`.
- `CasaAtualizar`: permite alterar parcialmente `nome`, `endereco` e `foto`.
- `CasaResposta`: devolve `id`, os dados da casa e o identificador do
  proprietário.

O proprietário é informado somente na criação. O schema de atualização não
permite trocar `fk_usuario_id`.

### `src/backend/services/casa.py`

A classe `ServicoCasa` concentra o acesso à tabela `casa` e implementa:

- criação de uma casa;
- busca por UUID;
- listagem paginada por `inicio` e `limite`;
- atualização parcial;
- exclusão;
- conversão da foto entre Base64, usado pela API, e o formato hexadecimal de
  `BYTEA` do PostgreSQL (`\x...`).

Uma foto ausente é mantida como `null`. Base64 inválido é rejeitado antes da
consulta ao banco. Na atualização, campos com valor `null` são ignorados; por
isso, a rota atual não permite remover uma foto existente enviando `null`.

### `src/backend/routers/casa.py`

O router usa o prefixo `/casas` e delega as operações para `ServicoCasa`:

| Método | Endpoint | Funcionalidade |
| --- | --- | --- |
| `POST` | `/casas/` | Cria uma casa |
| `GET` | `/casas/` | Lista casas com paginação |
| `GET` | `/casas/{id_casa}` | Busca uma casa por UUID |
| `PATCH` | `/casas/{id_casa}` | Atualiza parcialmente uma casa |
| `DELETE` | `/casas/{id_casa}` | Exclui uma casa |

O endpoint de criação retorna `201 Created`. O router está registrado em
`src/backend/main.py`.

## Regras e respostas de erro

- UUID ou payload inválido: `422` gerado pela validação do FastAPI/Pydantic.
- Foto em Base64 inválida: `400`.
- Atualização sem campos válidos: `400`.
- Casa inexistente em busca, atualização ou exclusão: `404`.
- Falha de inserção ou foto em formato inesperado no banco: `500`.

## Persistência

A tabela `Casa` foi criada em `docs/migrations/01.sql`. A migration
`02.sql` converteu seu identificador e a chave estrangeira de usuário para
UUID. A foto é armazenada em uma coluna `BYTEA`, e a exclusão do proprietário
é restringida enquanto houver uma casa vinculada a ele.

## Testes

O arquivo `src/backend/tests/test_casas_crud.py` registra uma aplicação
FastAPI isolada e substitui o Supabase por um banco em memória. Portanto, ele
valida as rotas, schemas, serviço e contrato esperado com o banco, mas não é
um teste de integração com um projeto Supabase real.

Os sete casos cobrem criação, conversão da foto, paginação, busca, atualização
parcial, exclusão, respostas de erro e contrato OpenAPI.

## Validação realizada

Os testes de Casa foram executados junto aos testes locais de Tarefa com:

```text
python -m pytest -q tests/test_casas_crud.py tests/test_tarefas_crud.py tests/test_servico_tarefa_unitario.py
```

Resultado conjunto: `18 passed`. Sete desses testes pertencem ao CRUD de
Casa. Foi emitido um aviso de depreciação do `TestClient` sobre `httpx`, sem
falha na suíte.
