# Inicialização local no Windows

## Objetivo e comportamento

- `scripts/dev.ps1` prepara e inicia o ambiente de desenvolvimento para Expo
  Go com um comando, a partir de qualquer diretório de execução.
- Verifica Node.js 24.3+, npm e Docker Compose; solicita autorização antes de
  instalar Node/Docker via WinGet e orienta sobre instalação manual e reinício.
- Preserva o `.env` existente, cria um a partir do exemplo quando necessário,
  gera o segredo de convites ausente e solicita a configuração do Supabase de
  teste sem imprimir valores privados.
- Seleciona um IPv4 da rede local, permite `-Ip`, detecta a porta 8081 ocupada,
  instala dependências quando necessário e sobe somente Redis e backend.
- Aguarda `/health` e um ping do backend ao Redis antes de iniciar Expo Go em
  LAN. URL da API e configuração Expo são temporárias e restauradas ao sair.
- `-CheckOnly` faz diagnóstico sem instalar ou iniciar serviços. Os containers
  permanecem disponíveis após encerrar o Expo; o README documenta como parar.
- Comandos interativos mantêm a saída nativa, sem redirecionamento para
  `Out-Host`. O Compose usa `--ansi never --progress plain` para evitar falhas
  de console no Windows durante o build. A mensagem de falha aponta para o
  erro original do Docker, sem presumir conflito de porta.
- `docker-compose.yml` fixa o Redis do backend no serviço local. O novo
  `src/backend/.dockerignore` exclui ambientes Python, caches e arquivos `.env`
  do contexto de construção da imagem.

## Validações

- Parser PowerShell: sem erros de sintaxe.
- `scripts/test-dev.ps1`: passou em PowerShell 7 e Windows PowerShell 5.1, com
  serviços simulados, cobrindo configuração,
  seleção de IP, recusa de instalação, criação/preservação do `.env`, ordem de
  inicialização, atualização das dependências e interrupção/restauração do
  ambiente após falhas.
- Diagnóstico real `scripts/dev.ps1 -CheckOnly`: identificou Docker Desktop
  ausente na validação inicial; não instalou programas nem iniciou serviços.
- Após a instalação do Docker pelo usuário, a chamada com `--ansi never
  --progress plain --dry-run up -d --build redis backend` passou no Docker
  Compose 5.5.1. Foi somente uma simulação do Compose, sem iniciar containers.
- Após a correção da chamada de console, o usuário confirmou que a execução
  de `scripts/dev.ps1` funcionou no seu ambiente. Essa confirmação é manual;
  não equivale a testes automatizados de cadastro, login ou persistência.

## Limitações

- A instalação automática via WinGet ainda não foi validada com instalação
  real; os testes dessa etapa usam comandos simulados.
- O script não cria nem modifica o banco e não aplica migrations. Healthcheck
  e ping do Redis não validam Supabase, cadastro ou login.
- Preparação do Supabase de teste, Expo Go no celular, configuração inicial do
  Docker/WSL, eventuais reinícios e acesso pela rede/firewall exigem a equipe.
- O agendador não é iniciado pelo script; serviços já em execução não são
  interrompidos automaticamente.

## Referências

- [Instalação via WinGet](https://learn.microsoft.com/en-us/windows/package-manager/winget/install)
- [Docker Desktop no Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
- [Desenvolvimento com Expo Go](https://docs.expo.dev/get-started/start-developing/)
