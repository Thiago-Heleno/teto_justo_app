# Calendário de tarefas — Sprint 4

## Objetivo e comportamento

Consultar as tarefas ativas da casa em uma visão mensal no topo da aba
**Tarefas**, antes do resumo, placar, filtros e lista. Ao voltar à aba, a
rolagem retorna ao topo. O contador de tarefas em aberto usa um bloco
horizontal compacto, com quantidade e rótulo.

- O atalho **Ver calendário** do Início abre `/tarefas`. A rota antiga
  `/calendario` redireciona para essa aba, mantendo a proteção por sessão e casa.
- Ativas são as tarefas `pendente` e `atrasada`. Os estados finais `finalizado`
  e `nao_feito` não aparecem.
- Cada tarefa aparece no dia do vencimento. `data_fixa` preserva a data
  cadastrada; os demais prazos e o dia atual usam o `timezone` da casa.
- É possível navegar entre meses, voltar para hoje e selecionar um dia para
  consultar nome, descrição, responsável, horário limite e status das tarefas.
- Tocar no cartão de uma tarefa da agenda abre o detalhe existente, com peso,
  prazo, responsáveis e as ações permitidas para o usuário. Ao voltar, o dia e
  o mês selecionados são preservados.
- O filtro **Somente minhas tarefas**, desativado por padrão, restringe a grade,
  as contagens e a agenda às tarefas atribuídas à conta logada, inclusive as
  compartilhadas. A seleção do dia e do mês é preservada ao alternar o filtro.
  Sem tarefas próprias ativas, a agenda informa que não há tarefas atribuídas
  ao usuário.
- Em telas pequenas, cada dia indica a quantidade de tarefas e a agenda fica
  abaixo do mês. Em telas largas, a agenda fica ao lado e os dias mostram até
  dois nomes, com indicação das tarefas adicionais. A agenda lista todas.
- As consultas são refeitas ao entrar na tela e pelo botão Atualizar.
  Uma atualização bem-sucedida preserva o dia selecionado. Falhas oferecem nova
  tentativa; requisições antigas são canceladas ao sair ou trocar de casa.

## Arquivos e decisões

- `src/frontend/src/components/calendario-tarefas.tsx`: seleção de data,
  calendário mensal, filtro pessoal e agenda; recebe os dados da aba Tarefas.
- `src/frontend/src/app/(app)/tarefas.tsx`: calendário no topo, contador compacto
  e consultas compartilhadas com a lista, incluindo carregamento e erro.
- `src/frontend/src/app/calendario.tsx`: redirecionamento da rota antiga.
- `src/frontend/src/services/tarefas-api.ts`: tipo da casa inclui `timezone`,
  já retornado pela consulta existente.
- `src/frontend/src/utils/calendario-tarefas.ts`: agrupamento das tarefas
  ativas, conversão para a data da casa, navegação e grade mensal.
- `src/frontend/src/app/_layout.tsx`: registro da rota protegida.
- `src/frontend/src/app/(app)/index.tsx`: atalho para o calendário na aba Tarefas.
- `src/frontend/scripts/calendario-tarefas.test.mjs` e
  `src/frontend/package.json`: sete testes unitários incluídos em `test:tarefas`.

A implementação reutiliza os componentes visuais e os serviços existentes:
consulta de casa, moradores e `GET /tarefas/casa/{id}`. Os filtros da lista de
tarefas não restringem o calendário. Não houve novas dependências, alterações
no backend ou migrações de banco.

A integração na aba reutiliza a consulta completa de tarefas e o contexto já
carregado, sem requisições extras. As cores amarelas locais das tarefas e dos
status foram preservadas na extração do componente.

O filtro pessoal reutiliza `carregarUsuarioAtual` (`GET /usuarios/eu`) e
`filtrarTarefas`, aplicando o responsável antes do agrupamento por dia. Alternar
o filtro usa os dados já carregados e não faz novas requisições.

A agenda usa `MotionPressable` e encaminha o ID para a seleção de tarefa da
própria tela. A consulta do detalhe aceita tarefas da lista filtrada e do
conjunto completo, permitindo abrir uma tarefa do calendário mesmo quando os
filtros da lista a excluem. A seleção de data fica na tela, associada à casa,
ao fuso e ao usuário, para sobreviver à abertura e ao fechamento do detalhe.

## Validação executada

Na abertura de detalhes pela agenda, a partir de `src/frontend`, com Node.js
24, os oito arquivos de teste de `test:tarefas` passaram: 69 testes unitários,
sem acesso ao banco. TypeScript (`tsc --noEmit`), ESLint dos dois arquivos
TypeScript alterados e `git diff --check`, a partir da raiz, também passaram.
O Node padrão da máquina não suporta os parâmetros da suíte; as validações
foram executadas com uma versão compatível já disponível no ambiente.

No navegador, com API fictícia local, foram conferidos: abertura pelo cartão
da agenda, descrição/peso/prazo/status/responsável no detalhe, retorno ao mesmo
dia em outro mês e abertura de tarefa ativa com a lista filtrada por
finalizadas. Os filtros foram preservados ao voltar; o filtro pessoal manteve
o dia selecionado e restringiu a agenda ao usuário. O botão de finalizar
apareceu para a responsável e ficou ausente na tarefa de outro morador.
Esta alteração não foi validada em dispositivo Android/iOS.

Na integração do calendário à aba Tarefas, a partir de `src/frontend`:

- `npm run test:tarefas`: 63 testes aprovados e uma falha ao carregar
  `scripts/notificacoes.test.mjs`, por ausência de `expo-notifications` na
  instalação local. Os testes de calendário e tarefas passaram.
- `npx tsc --noEmit`: bloqueado pela mesma dependência ausente e pelos tipos
  implícitos associados às notificações em `src/app/_layout.tsx`.
- ESLint nos cinco arquivos TypeScript alterados: aprovado.
- `git diff --check`, a partir da raiz: aprovado.
- A inicialização do servidor para inspeção visual foi rejeitada pela política
  de permissões do ambiente. Esta alteração não foi validada no navegador
  nem em dispositivo.

Validações anteriores à integração na aba:

Comandos executados a partir de `src/frontend`:

- `npm run test:tarefas`: 53 testes aprovados, incluindo seis testes novos
  de alinhamento da grade, anos bissextos, viradas de mês/ano, fusos horários,
  estados ativos, múltiplas tarefas e agenda vazia. Os testes de serviços
  existentes usam respostas simuladas, sem integração com banco real.
- `npx tsc --noEmit`: aprovado após o Expo regenerar os tipos locais das rotas.
- ESLint nos arquivos TypeScript alterados: aprovado, sem avisos.
- Prettier no novo arquivo de testes: aprovado.
- `git diff --check`: aprovado.

Validação manual no navegador com API fictícia local: acesso pelo Início e
pela lista, meses anterior/próximo, retorno para hoje, data fixa às 23:59,
detalhes do dia, exclusão de tarefas encerradas, troca de casa e fuso,
agenda vazia, recuperação de erro, preservação do mês ao atualizar e
redirecionamento para login no acesso sem sessão. A interface foi inspecionada em tela larga
e nas larguras de 390 e 320 pixels.

Validação do filtro pessoal, a partir de `src/frontend`: `npm run test:tarefas`
aprovou 56 testes, incluindo o caso de tarefas próprias, compartilhadas, de
outros moradores, sem responsável e encerradas, além da restauração da visão
completa e do resultado vazio para um morador sem tarefas. TypeScript, ESLint
da tela e Prettier dos arquivos de código alterados foram aprovados.
O filtro não foi validado manualmente no navegador ou em dispositivo.

## Limites

- A validação visual usou dados fictícios; não houve acesso ao banco real nem
  execução em dispositivo Android/iOS.
- O calendário mostra as tarefas existentes retornadas pela API. Não projeta
  ocorrências futuras de rodízios nem expande tarefas por todos os dias entre
  início e vencimento.
- Alterações feitas por outros moradores aparecem ao atualizar ou reabrir a tela;
  não há sincronização em tempo real.
