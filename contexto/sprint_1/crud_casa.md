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

- `CasaCriar`: recebe `nome`, `endereco`, `foto` opcional e `timezone` IANA
  opcional (padrão `America/Sao_Paulo`). O proprietário é obtido da sessão;
  `fk_usuario_id` não é aceito no payload.
- `CasaAtualizar`: permite alterar parcialmente `nome`, `endereco`, `foto` e
  `timezone`.
- `CasaResposta`: devolve `id`, os dados da casa e o identificador do
  proprietário, além de `timezone`.

O schema de atualização não permite trocar `fk_usuario_id`. A criação também
insere o proprietário em `pertencer` com `score` inicial zero e vínculo ativo.

### `src/backend/services/casa.py`

A classe `ServicoCasa` concentra o acesso à tabela `casa` e implementa:

- criação de uma casa;
- busca por UUID;
- listagem das casas próprias ou com vínculo ativo, paginada por `inicio` e
  `limite`;
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
| `GET` | `/casas/` | Lista casas próprias ou com vínculo ativo, com paginação |
| `GET` | `/casas/{id_casa}` | Busca uma casa do proprietário ou morador ativo por UUID |
| `PATCH` | `/casas/{id_casa}` | Atualiza parcialmente uma casa |
| `DELETE` | `/casas/{id_casa}` | Exclui uma casa |

O endpoint de criação retorna `201 Created`. O router está registrado em
`src/backend/main.py`.

## Regras e respostas de erro

- UUID ou payload inválido: `422` gerado pela validação do FastAPI/Pydantic.
- Foto em Base64 inválida: `400`.
- Atualização sem campos válidos: `400`.
- Usuário autenticado sem vínculo ativo ou propriedade em uma leitura: `403`.
- Usuário que não é proprietário em atualização ou exclusão: `403`.
- Casa inexistente em busca, atualização ou exclusão: `404`.
- Casa com dados vinculados na exclusão: `409`.
- Falha de inserção ou foto em formato inesperado no banco: `500`.

## Persistência

A tabela `Casa` foi criada em `docs/migrations/01.sql`. A migration
`02.sql` converteu seu identificador e a chave estrangeira de usuário para
UUID. A foto é armazenada em uma coluna `BYTEA`, e a exclusão do proprietário
é restringida enquanto houver uma casa vinculada a ele.

O contrato vigente, incluindo convites, entrada e saída, está em
`contexto/sprint_3/contrato_casa.md`. A coluna `pertencer.ativo` vem da
`docs/migrations/27.sql`, já presente na main; sua aplicação no banco não
foi verificada nesta tarefa.

## Testes

Os testes de contrato HTTP com banco em memória (`test_casas_crud.py`) foram
removidos do repositório. A cobertura atual de Casa está em:

- `src/backend/tests/test_servico_casa_unitario.py`: testes unitários de
  `ServicoCasa` com mock do cliente Supabase (criação, foto em Base64,
  busca, listagem, atualização, exclusão e moradores).
- `src/backend/tests/test_casa_integracao.py`: CRUD executado pelas rotas
  reais contra um projeto Supabase de teste.

## Validação

Na entrega original, os sete testes de `test_casas_crud.py` passaram junto
aos de Tarefa (`18 passed`). Esses números se referem a arquivos que não
existem mais; para validar hoje, rode a partir de `src/backend`:

```text
python -m pytest -q tests/test_servico_casa_unitario.py
python -m pytest -q tests/test_casa_integracao.py  # exige Supabase de teste
```
