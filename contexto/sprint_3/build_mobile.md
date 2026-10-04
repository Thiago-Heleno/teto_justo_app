# Build mobile pelo GitHub Actions

## Objetivo

Gerar APK Android e IPA iOS sem assinatura por execução manual no GitHub,
sem depender de login Expo, EAS ou certificados Apple para compilar.

## Arquivos e comportamento

- `.github/workflows/mobile-build.yml` gera os projetos nativos com Expo
  Prebuild e compila Android no Ubuntu 24.04 com Java 17 e iOS no macOS 26
  com Xcode 26.6. Ambas as plataformas usam Node 24 e `npm ci`.
- O APK Release inclui o JavaScript e usa a chave de teste padrão do template
  Expo. O IPA é arquivado com assinatura desativada e empacotado em `Payload`.
- Os builds são independentes: a falha de uma plataforma não cancela a outra.
  Os arquivos ficam nos artefatos da execução por 14 dias.
- `README.md` documenta execução, download e instalação. O workflow de Release
  via EAS existente continua separado; seu histórico está em
  [releases_mobile.md](../sprint_2/releases_mobile.md).

## Uso e credenciais

Após enviar o workflow à branch principal, abrir **Actions → Build APK e IPA
unsigned → Run workflow**, selecionar a branch e informar a URL pública HTTPS
da API. O ID da casa é opcional para funcionalidades legadas. Não é necessário
`EXPO_TOKEN`; as entradas são embutidas no app e não devem conter credenciais.

Baixar e extrair `TetoJusto-Android` e `TetoJusto-iOS-unsigned` em **Artifacts**.
O APK pode ser instalado para testes. Uma instalação assinada pelo EAS precisa
ser desinstalada antes, apagando os dados locais. O IPA precisa ser assinado
ao instalar via Sideloadly; não permite instalação direta ou envio ao TestFlight.

## Validações e pendências

O YAML foi analisado com `js-yaml`; trigger manual, permissões de leitura e
matriz foram conferidos. Todos os comandos passaram em `bash -n`, e
`git diff --check` não apontou erros.

A compilação nativa e a instalação dos artefatos ainda não foram executadas.
Precisam de uma execução no GitHub e teste em aparelhos. Esses builds usam
assinatura diferente da distribuição EAS e não substituem as credenciais do
workflow de Release.
