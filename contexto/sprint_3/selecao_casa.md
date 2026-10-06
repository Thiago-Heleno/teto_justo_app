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

## Emissão de convite no app

Na tela inicial da casa, **Convidar morador** aparece somente depois que
`GET /usuarios/eu` confirma que a conta é o proprietário (`fk_usuario_id`).
A identidade é consultada novamente ao voltar à aba; uma falha permite
repetir a consulta. O backend continua autorizando cada emissão em
`POST /casas/{id_casa}/convites`, sem receber cargo ou usuário do frontend.

- O clique gera um convite da casa ativa, bloqueando cliques repetidos.
  Não há emissão automática ao abrir a casa.
- O painel mostra o texto, a validade retornada pela API no horário local e
  instruções para a outra conta usar **Entrar por convite**. **Copiar convite**
  confirma a cópia, sem emitir outro convite. Na web, usa a área de
  transferência do navegador; no aplicativo nativo, `expo-clipboard`.
  Se a cópia falhar, o texto continua selecionável para cópia manual.
- Ao expirar, a ação de cópia é removida e **Gerar novo convite** fica
  disponível. Gerar outro convite não revoga os anteriores, conforme o
  contrato do backend. Um convite pode ser aceito por várias pessoas.
- Erros da API são exibidos no painel. `403` bloqueia novas emissões nessa
  abertura; `401` encerra a sessão pelo cliente compartilhado. Falhas de rede
  permitem tentar novamente.
- Fechar o painel, mudar de aba, trocar de casa ou sair descarta o convite
  exibido e cancela a requisição pendente. Isso não revoga um convite que já
  tenha sido emitido pelo servidor. O app não grava o convite em URL, logs
  ou armazenamento persistente; a cópia ocorre somente por ação do usuário.

A API exige `CASA_CONVITE_SECRET` configurado. Os convites expiram em 24 horas.
Não foram adicionados links/QR codes, envio automático ou cargos adicionais.

## Implementação

- `src/frontend/src/components/selecao-casa.tsx`: controle de acesso às abas,
  lista, escolha automática/manual, acesso à criação e à entrada por convite,
  carregamento, erros e nova tentativa. Um único estado escolhe qual
  formulário está aberto; a seleção bem-sucedida retorna às abas.
- `src/frontend/src/components/criar-casa.tsx`: formulário, validação local,
  erros por campo, bloqueio de envio repetido e recuperação após criação.
- `src/frontend/src/components/entrar-casa.tsx`: formulário de convite,
  validação, erros de entrada, bloqueio de envio repetido e abertura da casa.
- `src/frontend/src/components/convidar-morador.tsx`: verificação da conta,
  emissão de convite, cópia, validade, erros e descarte do painel.
- `src/frontend/src/app/_layout.tsx`: exige seleção da casa após autenticação.
- `src/frontend/src/app/index.tsx`: nome da casa ativa, ação de troca e acesso
  ao convite, com conteúdo rolável para acomodar o painel em telas pequenas.
- `src/frontend/src/services/casas-api.ts`: contrato da casa, listagem paginada
  e escolha inicial conforme preferência e quantidade de casas; criação
  autenticada com nome e endereço; entrada autenticada por convite; emissão
  autenticada com o ID da casa, recebendo `convite` e `expira_em`.
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

`expo-clipboard` foi acrescentado na versão compatível com o Expo SDK 57.
Aplicativos nativos compilados precisam ser reconstruídos para incluir o módulo.

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

## Validação consolidada do fluxo — 06/10/2026

- Exportação web de produção (`expo export --platform web`): passou, com
  seis rotas estáticas. TypeScript passou. ESLint dos arquivos do fluxo
  passou após normalizar temporariamente CRLF para LF; o checkout Windows
  usa CRLF e o Prettier exige LF. O formato original foi restaurado após
  a checagem, sem mudança de conteúdo no frontend.
- Os 60 testes do frontend passaram novamente. Os cenários de seleção,
  criação e entrada descritos acima também passaram no Chrome usando o
  site exportado e respostas de API simuladas.
- Backend: **334 testes passaram**, excluindo os arquivos `*_integracao.py`.
  Foi acrescentado ao `test_contrato_casa_router_unitario.py` um teste da
  jornada de duas contas, com login, criação, emissão/aceitação de convite,
  isolamento entre casas, restrição de administrador, logout e novo login.
  Ele utiliza a autenticação e os serviços da aplicação, substituindo somente
  o Supabase pelo banco em memória já usado pelos testes de contrato.
  Ruff do arquivo alterado passou.
- Uma rodada adicional conectou o site exportado à API FastAPI local por
  HTTP, sem interceptar respostas no navegador. Apenas a dependência do
  banco foi substituída por dados em memória; login, autorização, assinatura
  e verificação de convites foram executados pelos serviços da aplicação.
  Passaram: administrador automático, entrada de outra conta como morador,
  tarefas/moradores/placar da casa escolhida, descarte do rascunho de tarefa
  ao trocar de casa, restauração inclusive na rota de pontuação, logout,
  troca de usuário no mesmo navegador, perda de acesso, reativação do vínculo
  sem duplicação e sessão revogada. Nenhum erro JavaScript foi observado.
- As dependências locais ausentes foram instaladas a partir de
  `requirements-dev.txt`, incluindo `pytest` e `tzdata` já declarados pelo
  projeto. Não foi necessário alterar código de produção nem dependências.

Para repetir a suíte do backend, a partir de `src/backend`, com o ambiente
virtual ativado e as dependências de `requirements-dev.txt` instaladas:

```powershell
$env:SUPABASE_URL = "http://127.0.0.1:54321"
$env:SUPABASE_KEY = "unit-test-placeholder"
$env:PYTHON_DOTENV_DISABLED = "1"
python -m pytest -q -p no:cacheprovider tests --ignore-glob="*_integracao.py"
```

Use um terminal dedicado: essas variáveis são somente para a suíte sem
serviços externos. Os testes acima **não comprovam persistência no Supabase**.

### Validação da emissão pelo app

- TypeScript, ESLint dos arquivos alterados e exportação web de produção:
  passaram. A suíte do frontend passou com **66 testes**, incluindo seis
  novos casos de emissão (pedido autenticado, erros 403/404/503, sessão
  expirada e falha de rede).
- Chrome com API e área de transferência simuladas: botão exclusivo do
  proprietário, ausência de emissão automática, nova tentativa de consultar
  a conta, clique duplicado, convite somente para leitura, cópia sem novo
  POST, alternativa manual após bloqueio de cópia, expiração, nova emissão,
  erros 403/404/503/rede, sessão expirada e troca de casa durante a requisição
  passaram. O convite não foi persistido pelo app. Painel inspecionado em
  1280 × 900 e 390 × 844, sem transbordamento horizontal.
- Chrome conectado à API local com banco em memória: a conta proprietária
  criou a casa, gerou o convite pelo novo botão e acionou a cópia; a segunda
  conta aceitou pela interface, ganhou acesso como moradora e não recebeu o
  botão de emissão. Autorização, assinatura e verificação foram executadas
  pelos serviços da aplicação. O restante da jornada de troca de casa,
  restauração, isolamento e logout continuou passando, sem erros JavaScript.
- Os testes desta interface não gravaram no Supabase real. A cópia nativa
  em Android/iOS continua pendente de validação em dispositivo.

## Checagem pendente com banco real

Com a API apontando para um banco de testes isolado, siga a configuração do
`README.md`: migrations necessárias (incluindo `27.sql`), segredo de convites
no backend, URL da API no frontend e origem do site autorizada em CORS.

1. Entre com a conta A sem casas e crie uma casa. Confirme a abertura
   automática e a conta A como administradora.
2. Use **Convidar morador → Copiar convite** com a conta A. Em outro navegador,
   entre com a conta B, aceite o convite e confira que ela aparece como
   moradora, sem acesso ao botão de emissão.
3. Crie uma segunda casa com A, alterne entre as duas e confira tarefas,
   moradores e pontuação. B deve continuar sem acesso à segunda casa.
4. Recarregue a página e reabra o navegador com a sessão válida: a última
   casa acessível deve ser restaurada. Saia e entre com outra conta no mesmo
   navegador: a preferência anterior não deve ser reutilizada.
5. Confira convite inválido/expirado, erro de validação e sessão revogada.
   Confirme no banco a ausência de vínculos duplicados após repetir a entrada.

Para o deploy, a conexão de um repositório de conta pessoal com a Vercel
precisa ser feita pelo proprietário; acesso de colaborador não basta. No
plano Hobby, a Vercel não oferece colaboração para repositórios privados.
O responsável precisa conferir o plano e o acesso da equipe. Fontes oficiais:
[permissões do repositório](https://vercel.com/docs/git/vercel-for-github#personal-account-repositories)
e [colaboração no Hobby](https://vercel.com/docs/deployments/troubleshoot-project-collaboration#hobby-teams).

## Limites

A API publicada, a persistência no Supabase, a aplicação da migration `27.sql`
e os dispositivos Android/iOS não foram validados. Os testes de navegador
usaram Chrome no computador, inclusive com largura de celular. A restauração
confirma acesso consultando a lista; uma mudança de permissão depois que a
casa já foi aberta continua sujeita à autorização de cada endpoint.
