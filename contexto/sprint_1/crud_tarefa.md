# CRUD de Tarefa (Backend) — Sprint 1

## Resumo

Foi implementado o CRUD da entidade `Tarefa` no backend com FastAPI e
Supabase. Cada tarefa pertence a uma casa, mantém um vínculo principal com um
usuário em `fk_usuario_id` e pode ser atribuída a vários usuários por meio da
tabela associativa `atribuida`.

Os campos da API e do serviço estão padronizados em português e usam os nomes
do banco diretamente, sem `FIELD_MAP`.

## Estrutura implementada

### `src/backend/schemas/tarefa.py`

Foram definidos três contratos Pydantic:

- `TarefaCriar`: recebe `nome`, `descricao` opcional, `estado_atual`,
  `data_fim`, `fk_casa_id`, `fk_usuario_id` e a lista opcional
  `usuarios_atribuidos`.
- `TarefaAtualizar`: permite alterar parcialmente os dados da tarefa e suas
  atribuições, mas não permite trocar `fk_usuario_id`.
- `TarefaResposta`: devolve os dados persistidos e sempre apresenta
  `usuarios_atribuidos` como uma lista.

### `src/backend/services/tarefa.py`

A classe `ServicoTarefa` concentra o acesso às tabelas `tarefa` e `atribuida`
e implementa:

- criação da tarefa e de suas atribuições;
- busca por UUID;
- listagem paginada por `inicio` e `limite`;
- listagem filtrada por casa;
- atualização parcial da tarefa;
- substituição ou remoção das atribuições;
- exclusão da tarefa e de seus vínculos em `atribuida`.

`usuarios_atribuidos` não é gravado na tabela `tarefa`. O serviço separa esse
campo do restante do payload e persiste cada vínculo na tabela `atribuida`.
Identificadores repetidos são removidos antes da inserção.

Na atualização, omitir `usuarios_atribuidos` preserva as atribuições atuais.
Enviar uma lista substitui todas as atribuições, e enviar uma lista vazia
remove todos os usuários atribuídos.

### `src/backend/routers/tarefa.py`

O router usa o prefixo `/tarefas` e delega as operações para
`ServicoTarefa`:

| Método | Endpoint | Funcionalidade |
| --- | --- | --- |
| `POST` | `/tarefas/` | Cria uma tarefa e suas atribuições |
| `GET` | `/tarefas/` | Lista tarefas com paginação |
| `GET` | `/tarefas/casa/{id_casa}` | Lista as tarefas de uma casa |
| `GET` | `/tarefas/{id_tarefa}` | Busca uma tarefa por UUID |
| `PATCH` | `/tarefas/{id_tarefa}` | Atualiza a tarefa e/ou suas atribuições |
| `DELETE` | `/tarefas/{id_tarefa}` | Exclui a tarefa |

O endpoint de criação retorna `201 Created`. O router está registrado em
`src/backend/main.py`.

## Regras e respostas de erro

- UUID ou payload inválido: `422` gerado pela validação do FastAPI/Pydantic.
- Atualização sem campos informados: `400`.
- Tarefa inexistente em busca, atualização ou exclusão: `404`.
- Falha ao criar a tarefa ou suas atribuições: `500`.

## Persistência

As tabelas `Tarefa` e `Atribuida` foram criadas em
`docs/migrations/01.sql`. A migration `02.sql` converteu seus identificadores
e chaves estrangeiras para UUID. A migration `04.sql` definiu a geração de
`criado_em` pelo banco, e a migration `05.sql` criou a chave primária composta
de `Atribuida` e configurou a remoção em cascata dos vínculos quando uma tarefa
é excluída.

## Testes

- `src/backend/tests/test_tarefas_crud.py`: testes de contrato HTTP com uma
  aplicação FastAPI isolada e banco em memória. Cobrem criação, consulta,
  paginação, filtro por casa, atualização das atribuições, exclusão e uso dos
  campos em português.
- `src/backend/tests/test_servico_tarefa_unitario.py`: testes unitários de
  `ServicoTarefa` com mocks do cliente Supabase.
- `src/backend/tests/test_tarefas_integracao.py`: teste de integração que
  executa o CRUD pelas rotas reais contra um projeto Supabase de teste e limpa
  os registros temporários ao final.

Os dois primeiros arquivos não acessam serviços externos. O teste de
integração depende das variáveis de ambiente do Supabase e não foi executado
localmente nesta validação.

## Validação realizada

Os testes locais de Tarefa foram executados junto aos testes de Casa com:

```text
python -m pytest -q tests/test_casas_crud.py tests/test_tarefas_crud.py tests/test_servico_tarefa_unitario.py
```

Resultado conjunto: `18 passed`. Onze desses testes pertencem ao CRUD e ao
serviço de Tarefa. Foi emitido um aviso de depreciação do `TestClient` sobre
`httpx`, sem falha na suíte.
