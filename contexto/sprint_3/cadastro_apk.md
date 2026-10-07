# Cadastro de conta no APK — ECH-230

O aplicativo oferece “Criar conta” na tela de login. O formulário coleta nome,
e-mail, senha e confirmação; valida os campos antes do envio e chama o endpoint
público `POST /usuarios/` com somente `nome`, `email` e `senha`. O cadastro não
cria uma sessão. Após o sucesso, o aplicativo volta ao login com o e-mail
preenchido e uma confirmação. Erros de e-mail já cadastrado, validação da API e
conexão são exibidos no formulário.

O fluxo pré-autenticação é controlado por `src/frontend/src/app/_layout.tsx`,
sem criar uma rota que possa ser aberta após o login. A tela está em
`src/frontend/src/components/cadastro.tsx`; a chamada pública está em
`src/frontend/src/services/autenticacao-api.ts`.

## Verificação

- `npm run test:tarefas`: 41 testes passaram, incluindo corpo da requisição,
  erros e ausência de sessão após o cadastro.
- `npm run test:casas`: 27 testes passaram.
- `npx tsc --noEmit` e ESLint de todo o frontend com `endOfLine: auto`
  passaram.
- `npx expo export --platform android --output-dir dist/ech-230-check` gerou o
  bundle Android. A URL de API usada nessa exportação foi apenas local.
- `npm run lint` encontrou erros de fim de linha CRLF no checkout Windows;
  a verificação com essa regra ajustada ao checkout passou.

O cadastro em um APK instalado ainda precisa ser testado com uma API de teste
acessível e um dispositivo ou emulador Android. Este ambiente não tem Android
SDK nem dispositivo configurado.
