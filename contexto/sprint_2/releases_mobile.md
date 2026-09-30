# Releases móveis

## Objetivo

Gerar um APK Android e um IPA iOS para dispositivos e anexar os dois arquivos
ao GitHub Release de cada tag `v*`.

## Alterações e decisões

- `.github/workflows/mobile-release.yml` executa o EAS Build em nuvem para as
  duas plataformas, valida que ambas terminaram e publica os arquivos na tag.
- `src/frontend/eas.json` define distribuição interna e formato APK no Android.
- `src/frontend/app.json` vincula o projeto a `@teto-justo-app/teto-justo` e
  define `com.tetojusto.app` como identificador Android e iOS.
- `README.md` descreve a preparação da conta Expo, assinatura Apple e criação
  da tag. O IPA interno usa provisionamento para iPhones cadastrados.

## Validação e pendências

O JSON foi analisado localmente, `git diff --check` não apontou erros e o EAS
reconheceu o projeto vinculado. O secret `EXPO_TOKEN` foi cadastrado no GitHub;
seu valor não pode ser lido para validação. O keystore Android foi criado no
EAS e o primeiro build Android foi solicitado em 30/09/2026, mas ainda estava
em fila quando esta atualização foi feita:
https://expo.dev/accounts/teto-justo-app/projects/teto-justo/builds/6c4fe9b0-d307-46a0-afa8-04b05a01eeea.

O build iOS para dispositivos ainda depende de uma assinatura Apple Developer,
do cadastro dos iPhones e da configuração interativa das credenciais Apple.
Até isso ocorrer, o workflow que exige ambas as plataformas não pode publicar
um Release completo. A autenticação do app também não está pronta para um
build público: o token de sessão usado no desenvolvimento não deve ser
incluído como variável `EXPO_PUBLIC_*` no aplicativo distribuído.
