# CRUD da entidade Pertencer

## Resumo

Foi implementado o CRUD da entidade `Pertencer`, que representa o vínculo entre
um usuário e uma casa. O vínculo utiliza `fk_usuario_id` e `fk_casa_id` como
identificação composta e possui um `score` com valor inicial padrão `0`.

## Arquivos criados

### `src/backend/schemas/pertencer.py`

Foram criados os schemas:

- `PertencerCriar`: recebe os IDs do usuário e da casa e um `score` opcional,
  cujo padrão é `0`.
- `PertencerAtualizar`: recebe o novo valor do `score`.
- `PertencerResposta`: define o formato das respostas da API.

### `src/backend/services/pertencer.py`

Foi criada a classe `ServicoPertencer` com as operações:

- Criar um vínculo entre usuário e casa.
- Verificar se o vínculo já existe antes da criação.
- Buscar um vínculo por usuário e casa.
- Listar vínculos com paginação por `inicio` e `limite`.
- Atualizar o `score` de um vínculo.
- Excluir um vínculo.
- Retornar erros HTTP para vínculos duplicados, inexistentes ou falhas de
  inserção.

### `src/backend/routers/pertencer.py`

Foram criadas as rotas:

| Método | Endpoint | Funcionalidade |
| --- | --- | --- |
| `POST` | `/pertencer/` | Cria um vínculo |
| `GET` | `/pertencer/` | Lista os vínculos |
| `GET` | `/pertencer/{fk_usuario_id}/{fk_casa_id}` | Busca um vínculo |
| `PATCH` | `/pertencer/{fk_usuario_id}/{fk_casa_id}` | Atualiza o score |
| `DELETE` | `/pertencer/{fk_usuario_id}/{fk_casa_id}` | Remove um vínculo |

O endpoint de criação retorna `201 Created` e o endpoint de exclusão retorna
`204 No Content`.

## Arquivo editado

### `src/backend/main.py`

Foi adicionada a importação do router de `pertencer` e o registro:

```python
app.include_router(pertencer.router)
```

Nenhum código existente foi removido ou reestruturado.

## Validação

Os novos módulos e a integração com o `main.py` foram compilados com sucesso
usando o `compileall` do Python.
