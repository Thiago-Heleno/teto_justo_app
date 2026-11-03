# PWA e notificações web

## Objetivo

Permitir que a versão web seja adicionada à Home do iPhone/Android como PWA e
receba notificações Web Push, mantendo o fluxo Expo de Android/iOS.

## Alterações

- A barra de navegação web deixou de exibir `TETO JUSTO`; marca e navegação
  nativas não foram alteradas.
- O Expo web agora exporta manifesto, ícone de instalação, metadados
  standalone e service worker para exibir notificações e abrir tarefas.
- O frontend solicita permissão com ação explícita, registra assinatura
  `PushManager` e exibe orientação quando o navegador não suporta ou recusa
  notificações.
- O backend aceita tokens FCM Web como dispositivos `web`, além de tokens Expo
  existentes. A migration `34.sql` permite a nova plataforma.
- O envio web usa Firebase Admin SDK, enquanto Android/iOS continuam no Expo.
  `FIREBASE_SERVICE_ACCOUNT_JSON` fica somente em variável protegida.
- O service worker Firebase é gerado no `export:web` a partir da configuração
  pública `EXPO_PUBLIC_FIREBASE_*`.

## Validações

- `npm.cmd run test:tarefas` em `src/frontend`: 88 testes aprovados.
- `npx prettier --check` nos arquivos frontend alterados: aprovado.
- `pytest tests/test_notificacao_unitario.py -q` em `src/backend`: 87 testes
  aprovados.
- `ruff check` nos arquivos backend alterados: aprovado após ajuste de
  formatação.
- `npm.cmd exec -- expo export --platform web --output-dir web-build`:
  aprovado; manifesto e service worker foram copiados para a exportação.
- `tsc --noEmit`: mantém somente erros preexistentes de rotas tipadas em
  telas existentes; não apontou erro nos arquivos novos ou alterados desta
  tarefa.

## Limitações

Produção precisa servir o PWA em HTTPS e configurar chaves VAPID válidas. A
instalação e as notificações dependem do suporte do navegador e da permissão
do usuário.
