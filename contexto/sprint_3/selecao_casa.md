# Seleção da casa após o login — parte 2

## Objetivo e regras

O app consulta as casas do usuário antes de liberar as abas. A seleção usa
`GET /casas/`, com paginação, e substitui `EXPO_PUBLIC_CASA_ID` nas consultas
de tarefas, moradores e pontuação.

- Sem casas: mostra o estado vazio, atualização da lista e saída da conta.
- Uma casa: abre automaticamente.
- Várias casas: solicita uma escolha, exceto quando a última casa selecionada
  ainda está na lista de acesso retornada pela API.
- Reabertura com sessão válida: restaura a preferência somente após consultar
  novamente as casas. Uma falha nessa consulta oferece nova tentativa e não
  libera as abas com dados antigos.
- Casa salva ausente da lista: abre a única casa disponível ou solicita uma
  nova escolha se houver várias; lista vazia mantém as abas bloqueadas.
- **Trocar de casa**, no Início: sempre abre a lista, inclusive com uma única
  casa, sem sair da conta. A navegação das abas é desmontada para descartar
  dados, filtros e formulários locais da casa anterior.
- Logout, sessão expirada e novo login: limpam a casa ativa e sua preferência.

A regra acordada para as próximas etapas é abrir a casa criada ou aquela cujo
convite foi aceito. Os formulários de criação e entrada por convite ainda não
fazem parte desta implementação. Até lá, um usuário sem casas precisa obter
seu vínculo pela API antes de atualizar a lista.

## Implementação

- `src/frontend/src/components/selecao-casa.tsx`: controle de acesso às abas,
  lista, escolha automática/manual, carregamento, erros e nova tentativa.
- `src/frontend/src/app/_layout.tsx`: exige seleção da casa após autenticação.
- `src/frontend/src/app/index.tsx`: nome da casa ativa e ação de troca.
- `src/frontend/src/services/casas-api.ts`: contrato da casa, listagem paginada
  e escolha inicial conforme preferência e quantidade de casas.
- `src/frontend/src/services/sessao-store.ts`: estado global da casa, vínculo
  ao ciclo da sessão e serialização das gravações para coordenar seleção,
  logout e novo login.
- `src/frontend/src/services/casa-storage.ts`: persiste apenas o ID da casa,
  usando SecureStore no aplicativo nativo e localStorage na web, seguindo o
  padrão existente do token.
- `src/frontend/src/services/tarefas-api.ts`: usa a casa ativa da sessão.
- `README.md` e `.github/workflows/mobile-build.yml`: removem a configuração
  de casa fixa do uso e da geração de builds.

O backend permanece responsável por autorizar cada operação. Nenhuma rota,
migration ou dado do banco foi alterado.

## Validação executada

- TypeScript (`tsc --noEmit`): passou.
- ESLint direcionado aos arquivos de aplicação alterados: sem erros. Os
  scripts `.mjs` são ignorados pela configuração existente de lint.
- 49 testes passaram: casas (10), autenticação (12), API de tarefas (9),
  criação de tarefas (10), edição (3), filtros (2) e placar (3). Os testes
  substituem rede e armazenamento; não validam integração com banco real.
- O executor agregado encontrou `spawn EPERM` no ambiente restrito. Os
  arquivos foram então executados individualmente com Node e
  `--experimental-test-module-mocks`, preservando isolamento entre processos.
  `npm run test:casas` foi adicionado como entrada para a nova suíte.
- Verificação no Chrome com API simulada: login, múltiplas casas, consulta de
  tarefas da casa selecionada, troca, restauração, perda de acesso à casa
  salva, casa única, logout, estado vazio, erro e nova tentativa passaram.
  Nenhum erro de execução foi observado no navegador.
- Inspeção visual em 1280 × 900 e 390 × 844: seleção legível e sem
  transbordamento horizontal.

## Limites

A API real, a aplicação da migration `27.sql` e os dispositivos Android/iOS
não foram validados nesta etapa. A restauração confirma acesso consultando a
lista; uma mudança de permissão depois que a casa já foi aberta continua
sujeita às respostas de autorização de cada endpoint.
