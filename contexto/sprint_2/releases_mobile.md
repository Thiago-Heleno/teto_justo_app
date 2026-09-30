# Releases móveis

## Objetivo

Gerar um APK Android e um IPA iOS para dispositivos e anexar os dois arquivos
ao GitHub Release de cada tag `v*`.

## Alterações e decisões

- `.github/workflows/mobile-release.yml` executa o EAS Build em nuvem para as
  duas plataformas, valida que ambas terminaram e publica os arquivos na tag.
- `src/frontend/eas.json` define distribuição interna e formato APK no Android.
- `README.md` descreve a preparação da conta Expo, assinatura Apple e criação
  da tag. O IPA interno usa provisionamento para iPhones cadastrados.

## Validação e pendências

O JSON e o YAML foram analisados localmente e `git diff --check` não apontou
erros. A execução real ainda depende de definir os identificadores nativos,
vincular o projeto ao EAS, configurar as assinaturas de ambas as plataformas e
adicionar `EXPO_TOKEN` aos secrets do GitHub.

O login/logout agora obtém o token em tempo de execução; o app não lê
`EXPO_PUBLIC_TETO_JUSTO_TOKEN`. Isso não libera distribuição pública:
as pendências de autorização, limitação de login e validação nativa estão em
[autenticacao.md](./autenticacao.md). Não inclua credenciais como variáveis
`EXPO_PUBLIC_*` no aplicativo distribuído.
