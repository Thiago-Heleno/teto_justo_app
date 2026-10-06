# Seleção, criação e entrada em casas após o login

## Objetivo e regras

O app consulta as casas do usuário antes de liberar as abas. A seleção usa
`GET /casas/`, com paginação, e substitui `EXPO_PUBLIC_CASA_ID` nas consultas
de tarefas, moradores e pontuação.

- Sem casas: mostra o estado vazio, criação de casa, entrada por convite,
  atualização da lista e saída da conta.
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

A seleção inclui **Criar casa**, disponível também a quem já possui casas
pelo caminho **Início → Trocar de casa → Criar casa**. O formulário envia nome
e endereço para `POST /casas/` e abre a casa devolvida pela API, salvando-a como
preferência. A lista é consultada novamente ao voltar à seleção.

O nome e o endereço são obrigatórios e têm espaços externos removidos no
envio. Foto e fuso não são enviados nesta versão do formulário: o backend
usa foto ausente e `America/Sao_Paulo`. O administrador não é um campo do
formulário; o backend o obtém da sessão e cria o vínculo automaticamente.

Durante o envio, campos e botões ficam bloqueados, com proteção contra
submissões repetidas. Erros do backend são exibidos por campo quando há
localização na resposta de validação; os demais aparecem no formulário. Os
valores digitados são preservados. Se a criação for confirmada, mas salvar a
seleção falhar, **Abrir casa** tenta somente abrir a casa já criada, sem
repetir o POST. Uma falha de conexão sem confirmação orienta a conferir a
lista antes de reenviar, pois o backend não oferece chave de idempotência.

## Entrada por convite

**Entrar por convite** está disponível na seleção, inclusive quando o usuário
já possui casas, pelo caminho **Início → Trocar de casa**. O morador cola o
convite completo recebido do administrador; o formulário recusa texto vazio
ou composto apenas por espaços e envia somente `convite` no corpo de
`POST /casas/entrar`, removendo espaços externos. O usuário é identificado
pela sessão. O frontend não aceita somente o UUID da casa como autorização,
não decodifica nem valida a assinatura do convite e não atribui cargos.

A casa retornada é selecionada e persistida como preferência. Convites de
casas às quais o usuário já pertence seguem a resposta idempotente do
backend. A reativação do vínculo e a preservação de pontos são regras do
backend existente.

- `400`: mostra o erro de convite inválido/expirado junto ao campo e orienta
  a pedir um novo ao administrador.
- `422`: mostra a validação do campo e mensagens gerais da API.
- `404`, `409` e `503`: mostram a mensagem da API e permitem nova tentativa.
- Falha de conexão: preserva o texto e permite repetir a entrada.
- `401`: o cliente compartilhado encerra a sessão e volta ao login.

O envio repetido fica bloqueado enquanto há uma requisição em andamento.
Após a confirmação, o texto do convite é descartado. Se a seleção não puder
ser salva, **Abrir casa** reutiliza a casa devolvida pela API, sem aceitar o
convite novamente. Voltar ao seletor descarta o formulário; a nova consulta
atualiza as casas disponíveis. O convite não é colocado em URL, logs ou
armazenamento persistente.

Nesta etapa, a emissão continua pelo endpoint de administrador
`POST /casas/{id_casa}/convites`; não foi criada interface de emissão nem
suporte a links/QR codes. A API exige `CASA_CONVITE_SECRET` configurado e os
convites expiram em 24 horas, conforme o contrato existente.

## Implementação

- `src/frontend/src/components/selecao-casa.tsx`: controle de acesso às abas,
  lista, escolha automática/manual, acesso à criação e à entrada por convite,
  carregamento, erros e nova tentativa. Um único estado escolhe qual
  formulário está aberto; a seleção bem-sucedida retorna às abas.
- `src/frontend/src/components/criar-casa.tsx`: formulário, validação local,
  erros por campo, bloqueio de envio repetido e recuperação após criação.
- `src/frontend/src/components/entrar-casa.tsx`: formulário de convite,
  validação, erros de entrada, bloqueio de envio repetido e abertura da casa.
- `src/frontend/src/app/_layout.tsx`: exige seleção da casa após autenticação.
- `src/frontend/src/app/index.tsx`: nome da casa ativa e ação de troca.
- `src/frontend/src/services/casas-api.ts`: contrato da casa, listagem paginada
  e escolha inicial conforme preferência e quantidade de casas; criação
  autenticada com nome e endereço; entrada autenticada por convite.
- `src/frontend/src/services/api.ts`: mantém localização e mensagem dos erros
  de validação, além da mensagem geral já usada pelas outras telas. Não retém
  o campo `input` eventualmente retornado pelo backend.
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
- 60 testes passaram: casas (21), autenticação (12), API de tarefas (9),
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
- Verificação da criação no Chrome com API e falha de armazenamento
  simuladas: acesso sem casas, cancelamento sem gravação, campos vazios ou
  só com espaços, erros 422 por campo, erro geral, preservação dos valores,
  clique duplicado, abertura sem repetir o POST, casa criada na lista,
  restauração e sessão expirada passaram. Nenhum erro de execução foi
  observado. O formulário e seus erros foram inspecionados em 1280 × 900 e
  390 × 844, sem transbordamento horizontal.
- Verificação da entrada no Chrome com API e falha de armazenamento
  simuladas: lista vazia, cancelamento sem envio, convite vazio ou só com
  espaços, erros 400/404/409/422/503, falha de conexão, preservação do texto,
  clique duplicado, abertura sem repetir a entrada, descarte do convite,
  restauração, casa na lista, reentrada e sessão expirada passaram. A criação
  foi verificada novamente após a alteração na navegação e continuou
  passando. Nenhum erro de execução foi observado. Formulário e erros
  inspecionados em 1280 × 900 e 390 × 844, sem transbordamento horizontal.

## Limites

A API real, a aplicação da migration `27.sql` e os dispositivos Android/iOS
não foram validados nesta etapa. A restauração confirma acesso consultando a
lista; uma mudança de permissão depois que a casa já foi aberta continua
sujeita às respostas de autorização de cada endpoint.
