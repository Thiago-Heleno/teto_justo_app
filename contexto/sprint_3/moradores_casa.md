# Moradores da casa

## Objetivo e comportamento

A tela Início lista os moradores da casa ativa com nome e cargo. No contrato
atual, `casa.fk_usuario_id` identifica tanto o proprietário quanto o
administrador; por isso, essa pessoa aparece como **Proprietário ·
Administrador** e as demais como **Morador**. Não existe cargo de
administrador separado no backend.

- A ação **Remover** só aparece quando a identidade consultada pela tela
  corresponde ao administrador, e nunca aparece para o proprietário.
- O administrador confirma o nome do morador antes da remoção. Cancelar
  mantém a lista; durante o envio, novas remoções ficam bloqueadas.
- O cliente usa `DELETE /pertencer/{usuario}/{casa}`. Após `204`, remove a
  pessoa da lista exibida. Falhas preservam a lista e mostram a mensagem
  do backend, inclusive o `409` de tarefas pendentes ou atrasadas.
- A lista é consultada ao voltar à aba e pela ação **Atualizar moradores**.
  Erros de carregamento oferecem nova tentativa. Requisições são canceladas
  ao sair da aba; respostas canceladas não atualizam a tela.
- **Nova tarefa** usa a mesma consulta de moradores e não oferece mais dados
  fictícios. Ao voltar à aba, recarrega o contexto e descarta responsáveis
  e participantes selecionados que já não pertencem à lista.

## Arquivos e decisões

- `src/frontend/src/services/casas-api.ts`: tipo compartilhado de morador,
  listagem e remoção autenticadas; a consulta de detalhes reutiliza a listagem.
- `src/frontend/src/components/moradores-casa.tsx`: lista, cargos,
  confirmação, erros e atualização após remoção.
- `src/frontend/src/app/(app)/index.tsx`: incorpora o componente e reutiliza
  a identidade já consultada para as ações da casa.
- `src/frontend/src/services/tarefas-api.ts` e
  `src/frontend/src/app/(app)/nova-tarefa.tsx`: reutilizam a listagem e
  atualizam as opções ao voltar ao formulário.
- `src/frontend/scripts/casas.test.mjs`: verifica os contratos HTTP,
  autenticação, cancelamento encaminhado, resposta `204`, propagação de
  `403`/`409` e uma nova consulta de tarefas após remoção.

O backend existente continua responsável pela autorização e pelos bloqueios
de proprietário e tarefas abertas. Não foram alterados backend, banco ou
migrations.

## Validações realizadas

Comandos executados a partir de `src/frontend`:

- `node --experimental-test-module-mocks --test scripts/casas.test.mjs scripts/autenticacao-api.test.mjs scripts/filtros-tarefa.test.mjs scripts/tarefas-api.test.mjs scripts/criacao-tarefa.test.mjs scripts/edicao-tarefa.test.mjs scripts/reabertura.test.mjs`:
  90 testes passaram, usando respostas HTTP simuladas.
- `node node_modules/typescript/bin/tsc --noEmit`: passou após iniciar o
  Expo e atualizar seus tipos de rotas gerados, que estavam desatualizados
  para `/perfil`.
- ESLint nos cinco arquivos TypeScript alterados: passou.
- `git diff --check`, a partir da raiz: passou.

No navegador, com API local simulada, foram verificados: cargos, ausência de
remoção do proprietário, cancelamento da confirmação, mensagem `409`,
remoção bem-sucedida e atualização imediata, exclusão do removido das opções
de nova tarefa ao retornar à aba e ausência de botões de remoção para morador
comum.

Essas verificações não são integração com banco real. O fluxo não foi
executado em dispositivo nativo nem contra a API de produção.
