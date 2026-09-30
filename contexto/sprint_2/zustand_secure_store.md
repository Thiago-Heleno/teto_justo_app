# Zustand e Expo SecureStore no frontend

## Objetivo

Instalar `zustand` (estado global) e `expo-secure-store` (armazenamento seguro
do token de sessão) no frontend, deixando o armazenamento do token pronto.

## Alterações

- `src/frontend/package.json` e `package-lock.json`: `expo-secure-store`
  (`~57.0.4`, versão compatível com o Expo SDK 57, via `npx expo install`) e
  `zustand` (`^5.0.15`).
- `src/frontend/app.json`: plugin `expo-secure-store`, adicionado pelo
  `expo install`.
- `src/frontend/src/services/token-storage.ts`: `salvarToken`, `lerToken` e
  `removerToken`, sobre o SecureStore, com a chave `teto_justo_token`.

## Decisões e limitações

- O Zustand foi apenas instalado; nenhuma store foi criada, pois ainda não há
  estado global a compartilhar.
- `tarefas-api.ts` continua lendo o token de `EXPO_PUBLIC_TETO_JUSTO_TOKEN`.
  O `token-storage.ts` ainda não é chamado por nenhuma tela: a integração
  depende do fluxo de login. Ele não foi importado em `tarefas-api.ts` porque
  os testes `test:tarefas` rodam em Node puro, onde o módulo nativo não existe.
- O SecureStore funciona em Android e iOS; não está disponível na web.
- Mudar `app.json` (plugin) exige gerar o app nativo novamente; o Expo Go
  já inclui o módulo.

## Validação

Em `src/frontend`: `npx tsc --noEmit` e `npm run lint` sem erros;
`npm run test:tarefas` com 23 testes aprovados. O armazenamento em si não foi
executado em dispositivo ou emulador.
