# PWA e notificações web

## Objetivo

Permitir que a versão web seja adicionada à Home do iPhone/Android como PWA e
receba notificações Web Push, mantendo o fluxo Expo de Android/iOS.

## Alterações

### Frontend (`src/frontend`)

- `src/app/+html.tsx` substitui o HTML padrão do Expo Router. Precisa incluir
  `ScrollViewStyleReset`; sem ele o `#root` perde a altura e a tela fica em
  branco.
- PWA: `public/manifest.json` (standalone) com `public/icon-192.png` e
  `public/icon-512.png`, referenciados também pelo `apple-touch-icon`. Os
  ícones vêm de `assets/images/icon.png`; o Expo não publica esse arquivo com o
  mesmo nome, por isso não se aponta para ele.
- `src/services/web-push.web.ts` (Firebase Cloud Messaging) pede permissão,
  registra `/firebase-messaging-sw.js`, obtém o token FCM, cadastra em
  `POST /usuarios/eu/dispositivos` (`plataforma: "web"`) e guarda o token em
  `localStorage`. `src/services/web-push.ts` é um stub para o app nativo, que
  assim não empacota o Firebase.
- `src/services/notificacoes.ts` delega para esse módulo quando
  `Platform.OS === "web"`. Assim o botão do Perfil, a renovação do token após o
  login (`_layout.tsx`) e o logout (`sair()`) valem para web e nativo. No
  logout o token é removido da API e invalidado no Firebase.
- O botão "Ativar notificações" aparece no Perfil web quando o navegador
  suporta Web Push; senão, o Perfil orienta a instalar o app (no iPhone, o
  Web Push só funciona com o app na Tela de Início).
- `scripts/generate-firebase-sw.mjs` gera `public/firebase-messaging-sw.js` a
  partir de `EXPO_PUBLIC_FIREBASE_*`. O arquivo gerado está no `.gitignore` e
  roda em `npm run web` e `npm run export:web`.
- `firebase` passou a constar em `package.json`. A versão do SDK no service
  worker (`generate-firebase-sw.mjs`) deve acompanhar a do pacote.

### Backend (`src/backend`)

- `DispositivoPushRegistrar` aceita `plataforma: "web"` com token FCM de
  formato livre; android/ios continuam exigindo token Expo. A remoção
  (`DELETE /usuarios/eu/dispositivos`) aceita qualquer token.
- O cadastro é sempre por `token` (já `UNIQUE`), então repetir o cadastro não
  duplica e trocar de conta reassocia o aparelho.
- O envio web usa Firebase Admin SDK; Android/iOS continuam no Expo. Com
  `WEB_APP_URL` (HTTPS), a notificação traz um link para `/tarefas?abrir=<id>`;
  sem ela, tocar na notificação não abre a página.
- Migration `34.sql` só amplia o `CHECK` de `plataforma` para incluir `web`.

### Variáveis

- Frontend (`src/frontend/.env.local`, fora do Git): `EXPO_PUBLIC_FIREBASE_API_KEY`,
  `..._AUTH_DOMAIN`, `..._PROJECT_ID`, `..._STORAGE_BUCKET`,
  `..._MESSAGING_SENDER_ID`, `..._APP_ID`, `..._VAPID_KEY`.
- Backend (`.env.example`): `FIREBASE_SERVICE_ACCOUNT_JSON` (variável protegida;
  o arquivo `src/backend/firebase-service-account.json` está no `.gitignore`) e
  `WEB_APP_URL`.

## Validações

- `python -m pytest -q tests --ignore-glob='*_integracao.py'` em `src/backend`:
  656 testes aprovados, incluindo 3 novos (cadastro web repetido e remoção,
  envio FCM com link, envio sem link quando `WEB_APP_URL` não é HTTPS).
- `npm run test:tarefas` em `src/frontend`: 88 testes aprovados.
- `eslint src --rule "prettier/prettier: off"` e `tsc --noEmit`: sem erros nos
  arquivos alterados. O `prettier/prettier` aponta fim de linha (CRLF) em todo o
  projeto neste ambiente, inclusive em arquivos não alterados.
- `npm run export:web` e `expo export --platform android`: a exportação web
  inclui manifesto, ícones, service worker e o módulo `web-push.web.ts`; o
  bundle Android não contém o Firebase web.

## Limitações e pendências

- Não houve teste em navegador nem em iPhone: registro do service worker,
  obtenção do token FCM, permissão e entrega reais dependem de HTTPS, chaves
  VAPID válidas e do `FIREBASE_SERVICE_ACCOUNT_JSON` no backend.
- O deploy do frontend precisa rodar `npm run export:web` (não `expo export`
  direto); caso contrário o service worker não existe na publicação.
- Quem já aplicou a versão anterior da `34.sql` tem as colunas `endpoint`,
  `p256dh`, `auth`, o índice `uq_dispositivo_push_endpoint` e o check
  `dispositivo_push_formato_check`, sem uso. Não atrapalham; para remover:
  `DROP INDEX uq_dispositivo_push_endpoint; ALTER TABLE dispositivo_push DROP
  CONSTRAINT dispositivo_push_formato_check, DROP COLUMN endpoint, DROP COLUMN
  p256dh, DROP COLUMN auth; ALTER TABLE dispositivo_push ALTER COLUMN token SET
  NOT NULL;`
- A notificação web abre `/tarefas?abrir=<id>` na casa que estiver ativa no
  navegador; se for outra casa, a tarefa não é encontrada.
- Se a sessão expirar (401), o token web não é removido da API, como no nativo.
