# Sorteio de responsável por tarefa — backend

## Objetivo

Permitir escolher o responsável de uma tarefa **manualmente** (comportamento existente)
ou por **sorteio no backend**, para que o frontend apresente uma roleta e anime o
resultado efetivamente selecionado e salvo pela API.

A mudança foi implementada nas operações de criação e edição de **tarefas unitárias**.
Não modifica a lógica das tarefas rotativas ou o cálculo de pontuação.

## Arquivos alterados

- `src/backend/schemas/tarefa.py`: define `modo_atribuicao` (`manual` ou `aleatorio`),
  valida as combinações aceitas no `POST` e no `PATCH` e mantém `manual` como
  padrão na criação.
- `src/backend/services/tarefa.py`: sorteia um responsável, atribui o usuário à
  tarefa pelo fluxo já existente e reaproveita notificações e permissões.
- `src/backend/services/autorizacao.py`: reúne os IDs elegíveis usando os moradores
  com vínculo **ativo** na casa e seu administrador, sem duplicação.
- `src/backend/tests/test_schemas_tarefa_unitario.py`: cobre o contrato HTTP das
  opções de atribuição.
- `src/backend/tests/test_servico_tarefa_unitario.py`: cobre criação, edição,
  persistência da atribuição, notificações e bloqueios do sorteio.
- `src/backend/tests/test_servico_autorizacao_unitario.py`: cobre a busca dos
  candidatos elegíveis.

## Contrato da API

As rotas e os formatos de resposta existentes são preservados.

### 1. Criação — `POST /tarefas/`

**Escolha manual (inalterada):**

```json
{
  "nome": "Lavar a louça",
  "peso": 2,
  "prazo_dias": 3,
  "atraso_maximo": 2,
  "fk_casa_id": "00000000-0000-4000-8000-000000000001",
  "usuarios_atribuidos": ["00000000-0000-4000-8000-000000000002"]
}
```

O campo `modo_atribuicao` é opcional; sua ausência significa `manual`.
Também pode ser enviado explicitamente como `"modo_atribuicao": "manual"`.

**Escolha aleatória:**

```json
{
  "nome": "Lavar a louça",
  "peso": 2,
  "prazo_dias": 3,
  "atraso_maximo": 2,
  "fk_casa_id": "00000000-0000-4000-8000-000000000001",
  "modo_atribuicao": "aleatorio"
}
```

No sorteio, **não enviar `usuarios_atribuidos`**, nem como lista vazia.
O backend escolhe um único usuário elegível, cria a tarefa e insere a
atribuição na tabela relacional existente `atribuida`.

Resposta: HTTP `201`, com o mesmo `TarefaResposta` de antes. O resultado está em:

```json
{
  "usuarios_atribuidos": ["00000000-0000-4000-8000-000000000002"]
}
```

O JSON acima é apenas um **recorte** da resposta, que continua contendo os
demais campos usuais da tarefa.

### 2. Edição / novo sorteio — `PATCH /tarefas/{id_tarefa}`

Para sortear novamente e substituir o responsável de uma tarefa aberta:

```json
{ "modo_atribuicao": "aleatorio" }
```

Para atribuir manualmente:

```json
{
  "modo_atribuicao": "manual",
  "usuarios_atribuidos": ["00000000-0000-4000-8000-000000000002"]
}
```

O formato antigo também permanece aceito no `PATCH`:

```json
{ "usuarios_atribuidos": ["00000000-0000-4000-8000-000000000002"] }
```

No `PATCH`, enviar `modo_atribuicao: "manual"` sem a lista não é válido;
enviar `modo_atribuicao: "aleatorio"` junto com a lista também não é válido.

A API devolve o `TarefaResposta` atualizado com o responsável efetivo em
`usuarios_atribuidos`. Um novo sorteio **pode escolher a mesma pessoa**;
o sorteio não privilegia quem executou menos tarefas ou possui menos pontos.

## Elegibilidade, segurança e decisão técnica

- Só o **administrador da casa** pode criar, editar ou sortear responsáveis.
- Participam todos os usuários com `pertencer.ativo = true` na casa e também
  `casa.fk_usuario_id` (administrador). IDs repetidos não ganham chances extras.
- O sorteio usa `secrets.choice` em uma lista de IDs únicos e ordenados;
  a decisão acontece no backend e não depende do estado visual da roleta.
- A função `sortear_responsavel` recebe a lista pronta e não acessa banco.
  A busca dos elegíveis reutiliza a camada de autorização, com paginação.
- O método de atribuição é um **comando da requisição**, não uma propriedade
  persistida: `modo_atribuicao` não é escrito nas tabelas nem incluído em
  `TarefaResposta`. Não é necessária migração de banco.
- A criação mantém a notificação `tarefa_atribuida`; na edição, as notificações
  `tarefa_atribuida` e `atribuicao_removida` são disparadas quando há troca
  efetiva do responsável.
- A edição de tarefa em estado final continua bloqueada, inclusive por sorteio.

Erros principais: `422` para combinações inválidas de campos, `403` para usuário
sem permissão de administrador, `404` para casa/tarefa inexistente e `409` para
alteração de tarefa encerrada. Uma lista vazia de candidatos gera `422` no
sorteador (em uma casa válida, o administrador compõe a lista).

## Integração esperada no frontend (não implementada)

1. Oferecer `Manual` e `Roleta` na criação/edição de tarefa **unitária**.
2. Exibir a roleta com os candidatos elegíveis. A casa fornece o ID do
   administrador em `GET /casas/{id_casa}`; os moradores ativos estão em
   `GET /casas/{id_casa}/moradores`. Se o administrador não estiver nessa
   lista de moradores, **incluí-lo** na roleta. Seu nome pode ser obtido via
   `GET /usuarios/{id_administrador}` (com sessão autorizada).
3. Quando o usuário iniciar o sorteio, chamar `POST /tarefas/` ou
   `PATCH /tarefas/{id_tarefa}` com `modo_atribuicao: "aleatorio"` e **sem**
   `usuarios_atribuidos`.
4. **Somente após a resposta de sucesso**, usar
   `usuarios_atribuidos[0]` como resultado definitivo da roleta; animar até esse
   usuário. O frontend não deve sortear independentemente e enviar outro vencedor.
5. Em caso de falha da requisição, mostrar erro e não anunciar vencedor como
   tarefa atribuída. Evitar chamadas duplicadas, pois cada `PATCH` faz um
   novo sorteio e pode alterar o responsável novamente.
6. Ao receber a resposta, atualizar os detalhes/listagem da tarefa para
   refletir o responsável salvo.

**Observação:** A roleta é apenas a apresentação visual. Este backend não
expõe um endpoint de *pré-sorteio*; `POST` cria e atribui, e `PATCH` altera a
atribuição imediatamente. Se for necessária confirmação após a animação ou
cancelamento sem gravação, isso exige outro contrato de API.

## Validação executada

A partir de `src/backend`:

- `python -m pytest -q -p no:cacheprovider tests/test_schemas_tarefa_unitario.py tests/test_servico_autorizacao_unitario.py`: **64 testes passaram**.
- `PYTHONPATH=<diretorio-de-dubles>:. python -m pytest -q -p no:cacheprovider tests/test_servico_tarefa_unitario.py tests/test_servico_autorizacao_unitario.py tests/test_schemas_tarefa_unitario.py tests/test_schemas_rotatividade_unitario.py tests/test_servico_rotatividade_unitario.py`: **203 testes passaram**, usando dublês *temporários, externos ao repositório*, apenas para carregar os módulos `postgrest` e `firebase_admin` indisponíveis no ambiente. Os fluxos de serviço e os mocks de consultas existentes nos próprios testes foram executados.
- `python -m compileall -q` para os módulos modificados e seus testes: **sem erros de sintaxe**.

