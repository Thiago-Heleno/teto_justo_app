# Frontend — Teto Justo

Aplicativo React Native com Expo SDK 57 e Expo Router. As telas ficam em
`src/frontend/src/app/` e os componentes em `src/frontend/src/components/`,
considerando caminhos relativos à raiz do repositório.

## Iniciar no Windows

Na **raiz do repositório**, execute no PowerShell:

```powershell
.\dev.cmd
```

O script verifica as dependências, solicita a instalação do que faltar,
orienta a configuração do Supabase de teste no `.env`, inicia backend e Redis
e abre o Expo com a URL local da API configurada. No celular, use o Expo Go
compatível com o SDK 57 e a mesma rede do computador para ler o QR code.

O `dev.cmd` aplica uma política temporária apenas ao PowerShell que inicia o
script, sem modificar a política permanente do computador. O comando
equivalente, também a partir da raiz, é:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

As opções de IP, diagnóstico, encerramento e solução de problemas estão no
[guia de inicialização do projeto](../../README.md#iniciar-tudo-com-um-comando-no-windows).

## Executar somente o frontend

Para iniciar os serviços separadamente, siga a
[configuração manual no README principal](../../README.md#como-rodar-localmente),
incluindo backend, Redis e `EXPO_PUBLIC_API_URL`. No celular, essa URL precisa
usar um endereço acessível do computador, e não `localhost`.

Com o backend configurado e iniciado, execute em `src/frontend/`:

```powershell
npm.cmd ci
npm.cmd start -- --go --lan
```

Esses comandos iniciam apenas o frontend; não preparam o backend nem o banco.
