# Frontend de criação de tarefas — Sprint 2

## Objetivo e entrega

Criar um fluxo demonstrável para preencher tarefas e selecionar um ou mais
responsáveis, usando somente dados fictícios e estado local. Não há chamadas
à API nem persistência; recarregar a aplicação descarta a demonstração.

Para executar e visualizar, consulte
[tutorial_execucao_frontend.md](tutorial_execucao_frontend.md), com os caminhos
para navegador, Expo Go e compilação nativa. O tutorial foi conferido com os
scripts, a ajuda da CLI local e a documentação oficial em 20/09/2026; essa
atualização foi somente documental e não incluiu novos testes em aparelhos.

## Arquivos e comportamentos

- `src/frontend/src/app/nova-tarefa.tsx`: formulário com nome e peso obrigatórios,
  descrição opcional, data e horário obrigatórios e seleção múltipla de
  moradores. Exibe erros junto aos campos sem apagar valores, resumo da
  criação simulada e ação para iniciar outra tarefa com o formulário limpo.
- `src/frontend/src/data/tarefa-demonstracao.ts`: casa República Girassol e
  três moradores fictícios, incluindo a usuária da demonstração. A seleção
  utiliza IDs, sem seleção inicial.
- `src/frontend/src/constants/tarefa.ts`: opções de peso e seu tipo, mantidos
  em um único local para facilitar mudanças futuras.
- `src/frontend/src/utils/prazo-tarefa.ts`: modelo mínimo da tarefa e
  validação de calendário, horário e prazo futuro. O prazo é interpretado no
  fuso local e convertido para ISO; os campos correspondentes mantêm os
  nomes da API (`nome`, `descricao`, `data_fim`, `usuarios_atribuidos`).
- `src/frontend/src/components/app-tabs.tsx` e `app-tabs.web.tsx`: acesso
  “Nova tarefa”, preservando Home e Explore. A navegação web permite quebra
  de linha dentro da largura disponível.
- `src/frontend/package.json` e `package-lock.json`: alinhamento do
  `expo-router` de `^5.1.11` para `~57.0.21`, versão indicada pelo Expo 57
  instalado. A combinação anterior impedia a inicialização por ausência de
  `expo-router/internal/routing` e não fornecia as abas nativas usadas pelo
  projeto. Nenhuma biblioteca de formulário ou calendário foi adicionada.

## Decisões

- Campos de texto nos formatos `DD/MM/AAAA` e `HH:mm`, em 24 horas.
- Componentes e tema existentes, áreas seguras, rolagem e adaptação ao
  teclado. Responsáveis expõem rótulo e estado de checkbox para
  acessibilidade, além de marcação visual que não depende apenas da cor.
- A confirmação informa explicitamente que a tarefa foi criada nesta
  demonstração. Não existem autenticação, seleção de casa, listagem ou
  gravação de tarefas nesta entrega.
- IDs dos moradores são identificadores fictícios locais. A integração
  futura ainda precisa alinhar UUIDs reais, usuário/casa atuais, significado
  de `fk_usuario_id` e consulta de moradores por casa. A API atual já usa
  estados textuais; a criação integrada deverá alinhar o estado `pendente`.

## Validações da entrega inicial

- `npm ci --ignore-scripts --no-audit --no-fund`: instalação inicial
  concluída. A dependência de navegação foi atualizada posteriormente.
- `tsc --noEmit`: aprovado após o alinhamento do Router e a geração normal
  dos tipos de ambiente pelo Expo ao iniciar a aplicação.
- ESLint nos cinco arquivos TypeScript criados/alterados: aprovado.
- `npm run lint`: a verificação global falhou por formatação em arquivos
  existentes. A inspeção final com ESLint identificou 1.045 erros, todos de
  `prettier/prettier`, em arquivos fora da implementação, incluindo
  `expo-env.d.ts` gerado localmente. Não foi feita reformatação geral.
- Verificação pontual em Node, sem adicionar infraestrutura de testes:
  14 asserções de prazo aprovadas, cobrindo formato, datas inexistentes,
  ano bissexto, horários inválidos, passado, instante atual, futuro e
  conversão ISO no fuso `America/Sao_Paulo`.
- Conferência interativa no navegador: formulário vazio, nome apenas com
  espaços, data inválida, horário inválido, prazo passado, obrigatoriedade
  de responsável, marcação e desmarcação, criação com um e com vários
  responsáveis, descrição opcional, preservação após erros, resumo e
  limpeza para nova criação. Home e retorno pela navegação também foram
  verificados.
- Conferência visual web em largura de 390 px: navegação, rolagem, campos,
  responsáveis e botão acessíveis. Tema escuro conferido; o tema claro
  apareceu na renderização inicial, mas não recebeu uma rodada completa
  de validação.
- `expo export --platform all`: aprovado, gerando bundles Android/iOS
  com Hermes e exportação web, incluindo `/nova-tarefa`. Não equivale a
  build nativo instalado nem a teste em aparelho.
- `git diff --check`: aprovado.

## Ajuste de escopo e peso — 20/09/2026

- Reafirmado o escopo de tela de criação no frontend, com nome, descrição,
  peso, prazo e um ou mais responsáveis. A estrutura permanece simples para
  permitir revisão dos campos e regras conforme a task evoluir; não foi
  implementada edição de tarefas existentes nem integração com o backend.
- Adicionado peso obrigatório, sem seleção inicial, com seleção única,
  mensagem de validação, exibição no resumo e limpeza ao criar outra tarefa.
- Adotados provisoriamente os níveis `1`, `2`, `3`, `4`, interpretando peso
  como dificuldade com base na migration `07.sql`. A pergunta sobre peso
  significar dificuldade ou pontuação ainda não recebeu resposta. O campo
  local se chama `peso`; não há conversão automática para pontos nem envio
  à API. Essa definição permanece aberta para revisão com o usuário.
- TypeScript (`tsc --noEmit`) e ESLint dos três arquivos TypeScript deste
  ajuste: aprovados.
- Conferência interativa no navegador aprovada: peso inicialmente vazio,
  rejeição de envio sem peso preservando campos e responsáveis, troca de
  seleção de `1` para `3`, resumo com peso `3` e dois responsáveis e limpeza
  completa ao iniciar outra tarefa. Descrição vazia continuou aceita.
- A exportação móvel registrada acima pertence à entrega inicial; não foi
  repetida para esta alteração, nem houve teste em aparelho nesta sessão.

## Pendências reais

- A integração futura está detalhada em
  [pendencias_integracao_tarefas.md](pendencias_integracao_tarefas.md),
  separando contrato, autenticação, backend, banco e frontend. O arquivo foi
  conferido com o código local em 20/09/2026; sua criação foi apenas documental,
  sem alterar a aplicação, executar testes adicionais ou acessar o banco real.
- Não havia aparelho/emulador Android ou simulador iOS disponível nesta
  sessão. Validar teclado virtual, áreas seguras, toque, VoiceOver/TalkBack
  e temas claro/escuro nos dispositivos móveis antes de considerar esses
  critérios homologados.
- Resolver a formatação preexistente do frontend em uma tarefa separada.
