# Edição e atribuição de tarefas — Sprint 2

## Objetivo

Ajustar `PATCH /tarefas/{id_tarefa}` para editar peso, prazo e responsáveis,
impedindo responsáveis duplicados ou de outra casa.

## Alterações

- `schemas/tarefa.py`: campo `peso` (`Literal[1, 2, 3, 4]`) adicionado ao
  contrato da API. Obrigatório em `TarefaCriar`; opcional em
  `TarefaAtualizar`, já que o PATCH edita apenas os campos enviados;
  `TarefaResposta.peso` é `int` (obrigatório), pois não há tarefas
  legadas sem esse dado no banco.
- `services/tarefa.py`: `peso` é traduzido para a coluna `dificuldade` do
  banco (`docs/migrations/07.sql`) em `criar_tarefa` e `atualizar_tarefa`,
  e devolvido como `peso` em `_montar_resposta`. Corrigido também um bug
  nessa função, que chamava o dicionário da tarefa como função
  (`tarefa("dificuldade")`) em vez de indexá-lo (`tarefa["dificuldade"]`).
- `services/autorizacao.py`: novo método
  `ServicoAutorizacaoCasa.garantir_responsaveis_da_casa` — rejeita
  (`400`) UUIDs duplicados na lista de responsáveis e responsáveis que
  não pertencem à casa da tarefa. A checagem de pertencimento considera
  tanto os vínculos em `pertencer` quanto o dono da casa
  (`casa.fk_usuario_id`), que não é gravado em `pertencer` na criação da
  casa (`services/casa.py`).
- `services/tarefa.py`: `atualizar_tarefa` chama essa validação antes de
  apagar as atribuições antigas em `atribuida`, evitando perder os
  responsáveis existentes quando a nova lista é inválida.
- Prazo (`data_fim`) já era editável antes desta mudança; nenhuma
  alteração foi necessária nesse campo.

## Validação

- 15 testes unitários em `test_servico_tarefa_unitario.py` (4 novos:
  tradução de peso, responsáveis duplicados, responsável de outra casa,
  responsável válido sendo o dono da casa), todos aprovados.
- Suíte unitária completa (excluindo testes de integração que dependem
  de Supabase real): 79 testes aprovados.
- `test_tarefas_integracao.py` atualizado com `peso` nos payloads de
  criação existentes e um novo teste cobrindo duplicado, responsável de
  outra casa e responsáveis válidos (morador vinculado e dono da casa).
  Não executado localmente — depende de um Supabase de testes.

## Atualização — 21/09/2026: validação também no `POST`

`criar_tarefa` (`POST /tarefas/`) passou a chamar
`garantir_responsaveis_da_casa` também, antes de inserir a tarefa — assim
não é mais possível criar uma tarefa já nascendo com responsável duplicado
ou de outra casa (mesma regra que já valia para o `PATCH`). A validação
acontece antes do `insert`, então uma tarefa inválida nem chega a ser
criada. Testes novos em `test_servico_tarefa_unitario.py` (unitário) e
`test_tarefas_integracao.py` (`test_criar_tarefa_rejeita_responsaveis_invalidos`,
não executado neste ambiente).

## Pendência

- `GET /casas/{id_casa}/moradores` continua não implementado; é a outra
  tarefa do backlog relacionada a este fluxo.
- Testes de integração não executados neste ambiente; validar contra um
  Supabase de testes antes do merge.
