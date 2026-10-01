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
  `removerToken`, com a chave `teto_justo_token`. Em Android e iOS usa o
  SecureStore; na web usa `localStorage`, escolhido por `Platform.OS`.

## Decisões e limitações

- A integração foi concluída no fluxo de login/logout:
  `sessao-store.ts` compartilha a sessão com Zustand e chama o armazenamento.
  `api.ts` usa o token obtido em execução, removendo a dependência da variável
  `EXPO_PUBLIC_TETO_JUSTO_TOKEN`.
- Os testes em Node substituem somente o módulo de armazenamento nativo por
  funções em memória, sem carregar React Native. O comando usa
  `--experimental-test-module-mocks` no Node 24.
- Veja [autenticacao.md](./autenticacao.md) para os comportamentos e validações
  da integração.
- O SecureStore não existe na web. Lá o token fica em `localStorage`, legível
  por qualquer script da página (exposto a XSS). Serve para desenvolvimento e
  demonstração; para produção na web, o caminho recomendado é um cookie
  `HttpOnly` emitido pelo backend, que hoje usa `Authorization: Bearer`.
- Mudar `app.json` (plugin) exige gerar o app nativo novamente; o Expo Go
  já inclui o módulo.

## Validação

Em `src/frontend`: TypeScript e lint dos arquivos alterados aprovados;
`npm run test:tarefas` com 36 testes aprovados. O fluxo de armazenamento web
foi exercitado em navegador com API simulada. O armazenamento nativo ainda não
foi executado em dispositivo ou emulador. Os detalhes do lint geral e as demais
validações estão em [autenticacao.md](./autenticacao.md).
