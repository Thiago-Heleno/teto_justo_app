# Teto Justo

![Ícone do aplicativo Teto Justo](./icon.png)

O **Teto Justo** é um aplicativo para organizar a convivência em casas
compartilhadas. A plataforma permite cadastrar casas e seus moradores, criar e
atribuir tarefas, além de acompanhar as sessões e responsabilidades de cada
pessoa — tornando a divisão das atividades do lar mais clara e justa.

## Protótipo

O fluxo e as telas do aplicativo estão disponíveis no
[Figma](https://www.figma.com/design/xMTN0YQQvJrjXXuPWrQhMr/Untitled?node-id=0-1&t=9VOn0ieYSl2Ssmk3-1).

## Tecnologias

- **Frontend:** React Native, Expo, Expo Router e TypeScript. Estado global com Zustand e token de sessão guardado com Expo SecureStore no celular e `localStorage` na web. Cadastro, login e logout integrados à API.
- **Backend:** Python, FastAPI, Pydantic e Uvicorn.
- **Dados:** Supabase.
- **Qualidade:** ESLint, Prettier, Ruff, Bandit e Pytest.
- **Containerização:** Docker e Docker Compose.

## Arquitetura

```mermaid
flowchart LR
    RN[React Native<br/>Frontend] <--> API[FastAPI<br/>Backend]
    API <--> SB[(Supabase)]
```

O app React Native consome a API FastAPI, que concentra as regras de negócio e
acessa o Supabase para persistir os dados.

## Como rodar localmente

O aplicativo abre a tela de login e consulta as casas do usuário antes de
liberar as abas. Uma única casa é aberta automaticamente; com várias, o
usuário escolhe. A última escolha é lembrada enquanto a sessão continuar
válida e a casa permanecer acessível. **Trocar de casa**, no Início, volta à
seleção; sair da conta apaga a preferência.

No Windows, use o [comando de inicialização](#iniciar-tudo-com-um-comando-no-windows)
para iniciar backend, Redis e Expo juntos. As instruções manuais abaixo são
uma alternativa para executar os serviços separadamente.

Na tela de login,
**Criar conta** abre o formulário de cadastro; após criar a conta, entre com
o e-mail e a senha informados. O endpoint público `POST /usuarios/` também
está disponível na documentação interativa `/docs` do backend. Na seleção,
**Criar casa** abre o formulário de nome e
endereço. Após a criação, a casa é aberta automaticamente e o criador vira
administrador pela sessão autenticada. Os erros de validação aparecem junto
aos campos, preservando os dados digitados. Quem já está numa casa pode usar
**Trocar de casa → Criar casa**. Para participar de uma casa existente, use
**Entrar por convite** na seleção, cole o convite do administrador e confirme.
A casa é aberta automaticamente após a aceitação. Erros de convite inválido
ou expirado, casa removida e serviço indisponível aparecem no formulário.

Na tela inicial da casa, **Convidar morador** aparece para o proprietário,
que é o administrador. O botão gera o convite, mostra sua validade e permite
usar **Copiar convite** para enviá-lo a outra pessoa. Quem recebe usa
**Entrar por convite** na seleção de casas. O convite pode ser usado por mais
de uma pessoa e expira em 24 horas. A API confirma a permissão em cada emissão;
moradores não podem convidar. Links, QR codes e envio automático não estão
implementados. O endpoint `POST /casas/{id_casa}/convites` continua disponível
para uso direto pela API.

### Pré-requisitos

- Para o frontend: Node.js e npm; o projeto utiliza Expo SDK 57;
- Para o backend: Python 3 e um projeto Supabase com as variáveis de acesso;
- Para o login: Redis compartilhado entre as instâncias do backend;
- Docker Desktop com Docker Compose para usar o script de inicialização;
  na execução manual sem containers, Python e Redis precisam estar disponíveis.

### Iniciar tudo com um comando no Windows

Na raiz do repositório, execute no PowerShell:

```powershell
.\dev.cmd
```

O iniciador `dev.cmd` chama `scripts/dev.ps1` com uma política de execução
temporária, válida apenas para o processo iniciado. Assim, não é preciso
liberar scripts permanentemente nem executar como administrador para abrir
o script. Instalações de dependências ainda podem solicitar elevação.

Se preferir chamar o PowerShell diretamente, o comando equivalente é:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

Se o computador tiver uma política de grupo que bloqueia scripts, essa política
continua valendo; nesse caso, solicite a liberação ao administrador responsável.

O script verifica Node.js 24.3 ou superior, npm e Docker Desktop com Compose.
Se faltar Node ou Docker, pede confirmação para instalar pelo WinGet. Sem
WinGet, informa o site oficial para instalação manual. O instalador pode pedir
permissão de administrador; Docker/WSL ou virtualização podem exigir uma
configuração adicional e reinício. Nesses casos, conclua a preparação e rode
o mesmo comando novamente. Python e Redis são executados nos containers.

Na primeira execução, o script cria `.env` a partir de `.env.example`, caso
ele não exista. Preencha nesse arquivo `SUPABASE_URL` e `SUPABASE_KEY` (ou
`SUPABASE_SECRET_KEY`) com um **projeto Supabase de teste** e pressione Enter
no terminal para continuar. Credenciais existentes são preservadas; um segredo
de convites é gerado localmente somente quando estiver ausente. Nenhum valor
privado é mostrado pelo script.

Depois, o script instala as dependências com `npm ci`, inicia backend e Redis,
aguarda `/health`, verifica o acesso do backend ao Redis e abre o Expo com QR
code. As próximas execuções reutilizam a instalação do frontend enquanto
`package.json`, `package-lock.json` e a versão do Node não mudarem. A URL da API
e o IP anunciado pelo Expo são definidos apenas para essa execução; arquivos
de configuração do frontend não são alterados.

No celular, instale o [Expo Go compatível com o SDK 57](https://expo.dev/go),
conecte-se à mesma rede do computador e leia o QR code. Siga as instruções de
login exibidas pelo Expo quando necessário. Se houver mais de uma rede, o script
pede para escolher. Para indicar o IPv4 manualmente, ainda na raiz:

```powershell
.\dev.cmd -Ip 192.168.1.10
```

Substitua pelo IPv4 do computador na rede do celular. VPN, Wi-Fi com isolamento
de dispositivos e firewall podem impedir a conexão. Libere Node/Docker e as
portas TCP 8000 e 8081 somente na rede privada utilizada para desenvolvimento.
Antes de ler o QR, confira no navegador do celular o endereço `/health` mostrado
no terminal. Um túnel do Expo, sozinho, não torna o backend local acessível.

O script **não cria banco, não aplica migrations e não inicia o agendador de
penalidades/rotatividade**. A validação de `/health` e do Redis não comprova as
credenciais, a conectividade ou o esquema do Supabase; cadastro e login devem
ser conferidos no ambiente de teste preparado pela equipe. O comando usa
HTTP na rede local e não substitui hospedagem HTTPS para um APK distribuído.

Para apenas conferir dependências e configuração, sem instalar, editar arquivos
ou iniciar serviços, execute na raiz (código de saída 1 indica pendência):

```powershell
.\dev.cmd -CheckOnly
```

Ao encerrar o Expo com Ctrl+C, os containers continuam disponíveis. Para
pará-los sem apagar volumes, execute na raiz:

```powershell
docker compose stop backend redis
```

Os testes do script podem ser executados na raiz com
`.\scripts\test-dev.ps1`. Eles simulam instaladores e serviços; não acessam
Supabase, não sobem containers nem instalam programas.

### 1. Configure as variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto com as credenciais do seu projeto
Supabase:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-chave-do-supabase
REDIS_URL=redis://localhost:6379/0
```

Não versione esse arquivo nem exponha as credenciais.

No Docker Compose, o backend recebe automaticamente `REDIS_URL` apontando
para o serviço `redis` local, independentemente do valor no `.env`. O Redis não
publica porta no host. Fora do Compose, use uma instância Redis protegida
e a respectiva URL; `rediss://` habilita TLS. Sem Redis disponível, o login
responde `503` em vez de aceitar tentativas sem limite. Cinco falhas por e-mail
ou vinte por IP em quinze minutos respondem `429` com `Retry-After`. O backend
usa o IP da conexão; se houver proxy, configure somente os endereços de proxy
confiáveis no Uvicorn para que cabeçalhos encaminhados não possam ser forjados.
Consulte o [roteiro de implantação da ECH-205](./contexto/sprint_3/seguranca_pos_login.md)
antes de distribuir o app.

Para emitir e aceitar convites de casa, configure também
`CASA_CONVITE_SECRET` no ambiente do backend. Gere um segredo aleatório com ao
menos 32 bytes, por exemplo a partir da raiz do repositório:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Salve o resultado somente no `.env` local ou no gerenciador de segredos do
ambiente; nunca no frontend, no repositório ou em logs. O mesmo segredo deve
ser usado por todas as instâncias do backend. Se ele estiver ausente ou for
curto demais, as rotas de emitir e aceitar convites respondem `503`; as demais
rotas continuam disponíveis. Trocar o segredo invalida os convites emitidos
anteriormente. Os convites expiram em 24 horas; consulte o
[contrato da casa](./contexto/sprint_3/contrato_casa.md) para as rotas e erros.

O backend também depende de `pertencer.ativo`, adicionado pela
`docs/migrations/27.sql` da PR #99. A aplicação dessa migration no banco não
foi verificada nesta Task 207. Antes de implantar, confirme o estado do
ambiente e siga a [revisão de casa e pertencer](./contexto/sprint_2/revisao_casa_pertencer.md).

Antes de iniciar o backend com um banco existente, confira quais migrations de
`docs/migrations/` já foram aplicadas. A sequência dos arquivos é `14.sql`,
`15.sql`, `16.sql`, `17.sql` e `18.sql`, respeitando as que já constam do banco.
`18.sql` cria as tabelas e colunas usadas pela rotatividade automática. Não
execute migrations já aplicadas nem aplique alterações sem revisar o estado do
banco. O arquivo `19.sql` reconcilia o saldo com o histórico de eventos e deve
ser aplicado somente depois de revisar `GET /casas/{id}/auditoria-score`. Veja o
[resumo da sprint 2](./contexto/sprint_2/alinhamento_tarefas_pontuacao.md).

### 2. Inicie o backend

Em um terminal, execute:

```powershell
cd src/backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

A API ficará disponível em `http://127.0.0.1:8000`. Para confirmar que está
ativa, acesse `http://127.0.0.1:8000/health`.

Para o navegador em outra origem, defina `CORS_ORIGINS` no `.env` do backend
com as origens separadas por vírgula (por exemplo,
`http://localhost:8081,http://127.0.0.1:8081`).

#### Rotina agendada de penalidades

Um agendador externo pode chamar `POST /jobs/penalidades`. Configure
`PENALIDADE_JOB_TOKEN` no ambiente do backend e envie o mesmo valor no
cabeçalho `X-Penalidade-Job-Token`. Sem o segredo, o endpoint fica desativado;
não use o token em logs nem o exponha ao frontend.

Para desenvolvimento local, cada pessoa cria seu próprio token no `.env` local
da raiz do repositório; não é necessário compartilhar tokens entre
desenvolvedores. Gere um valor aleatório com Python:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copie o resultado para `PENALIDADE_JOB_TOKEN` no `.env` local e reinicie o
backend. `.env.example` documenta a variável, mas seu valor real não deve ser
preenchido nem commitado. Para um ambiente compartilhado, o responsável pela
implantação deve cadastrar o mesmo segredo no armazenamento seguro de variáveis
do backend e do agendador; compartilhe o acesso pelo gerenciador de segredos da
equipe, nunca por commits, mensagens ou logs.

Um teste manual em PowerShell pode usar uma variável de ambiente já configurada
na sessão, sem gravar o valor no comando:

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/jobs/penalidades" `
  -Headers @{ "X-Penalidade-Job-Token" = $env:PENALIDADE_JOB_TOKEN }
```

A rotina marca tarefas vencidas como `atrasada` e, após ultrapassar o atraso
máximo, como `nao_feito`. Chamadas repetidas são seguras: a atualização compara
o estado e as regras atuais da tarefa, e não gera `score_event` nem altera o
saldo. O desconto de `100 / (atraso_maximo + 1)` por dia é calculado no momento
da conclusão, onde o crédito é registrado uma única vez. O agendamento em si
deve ser configurado no serviço externo que fará a chamada HTTP.

#### Rotatividade automática

O endpoint `POST /jobs/rotatividades` processa as ocorrências vencidas das
configurações ativas e é destinado a um agendador externo. Configure
`ROTATIVIDADE_JOB_TOKEN` no backend; o agendador deve enviar o mesmo segredo no
cabeçalho `X-Rotatividade-Job-Token`. Não exponha nem registre esse token.

Para testar a integração com o banco, configure `SUPABASE_URL` e
`SUPABASE_KEY` no `.env` da raiz, aplique as migrations necessárias (incluindo
`18.sql`) e execute o teste a partir de `src/backend`:

```powershell
python -m pytest -q tests/test_rotatividade_integracao.py
```

Use somente um projeto Supabase descartável/de teste com acesso de escrita
`service_role`. O teste cria e remove usuários, casa, configuração, tarefa e
atribuição; também chama o job, confere os registros persistidos e valida que
uma segunda execução não duplica a ocorrência. Como o job processa todos os
rodízios ativos, o teste exige que o banco não tenha outros rodízios ativos.
Não o execute em produção nem num banco compartilhado com dados reais.

Como alternativa, a partir da raiz do repositório, execute o backend com
Docker:

```powershell
docker compose up --build backend
```

#### Agendador dos jobs (Docker)

O serviço `agendador` do `docker-compose.yml` chama os dois jobs uma vez por dia,
às 03:05 UTC (00:05 em Brasília): `POST /jobs/rotatividades` e
`POST /jobs/penalidades`. Os horários ficam em `src/agendador/crontab`. Ele lê
`ROTATIVIDADE_JOB_TOKEN` e `PENALIDADE_JOB_TOKEN` do mesmo `.env` do backend, e
os dois precisam ter valor, senão o backend responde `503` e o erro aparece no
log do agendador.

```powershell
docker compose up --build
```

Como o banco é compartilhado e o bloqueio contra execução simultânea existe só
dentro de um backend, deixe o agendador ligado em **uma única máquina**. Quem
não deve rodar o agendador sobe somente o backend, com
`docker compose up --build backend`. Para acompanhar as chamadas, use
`docker compose logs agendador`.

### 3. Inicie o frontend

Abra um terminal na raiz da sua cópia do repositório e instale as dependências
registradas no arquivo de lock:

```sh
cd src/frontend
npm ci
```

Faça essa instalação na primeira execução ou após receber alterações nas
dependências. Execute os próximos comandos dentro de `src/frontend`.

Para carregar a tela **Tarefas** com dados reais, crie
`src/frontend/.env.local` (esse arquivo é ignorado pelo Git):

```env
EXPO_PUBLIC_API_URL=http://127.0.0.1:8000
```

`EXPO_PUBLIC_CASA_ID` não é mais utilizado. Tarefas, moradores e pontuação
usam a casa selecionada após o login.

Entre com o e-mail e a senha da sua conta. O token é recebido de
`POST /sessoes/login` e salvo no SecureStore (celular) ou no `localStorage`
(web). O aplicativo não lê mais `EXPO_PUBLIC_TETO_JUSTO_TOKEN`; remova essa
variável de configurações antigas. No celular, substitua `127.0.0.1` pelo IP
da máquina na rede local.

A sessão expira em 24 horas. **Sair da conta** revoga a sessão atual por
`POST /sessoes/logout`. Tokens antigos armazenados em texto puro no banco
deixaram de autenticar: faça login para obter uma sessão nova. O CRUD
`/sessoes/` e `/sessoes/{id}` foi removido.

No PowerShell, se `npm` ou `npx` forem bloqueados pela política de scripts,
use `npm.cmd` e `npx.cmd`, respectivamente. No macOS e Linux, use os comandos
sem `.cmd`.

#### No navegador

```sh
npm run web -- --port 8081
```

Mantenha o terminal aberto e acesse
[Nova tarefa](http://localhost:8081/nova-tarefa), ou escolha **Criar**
na navegação do app. O formulário contém nome, descrição opcional, peso de
1 a 3 e prazo de 1 a 5 dias. Uma tarefa **Comum** tem um responsável; uma
**Rotativa** recebe pelo menos dois participantes, ordem ajustável e um ou
mais dias da semana, com repetição a cada 1, 2, 3 ou 4 semanas (por exemplo,
segunda-feira a cada 2 semanas). Quatro semanas correspondem a 28 dias,
aproximadamente um mês. Com a API configurada, **Criar tarefa** grava apenas
tarefas comuns. A opção rotativa mostra uma prévia local e não inicia um
rodízio. Sem a API, **Conferir tarefa** mostra uma prévia em memória.

Se a porta estiver ocupada, use a instância já aberta ou inicie com
`npm run web -- --port 8082` e ajuste a porta no endereço do navegador.

#### No celular com Expo Go

Instale o **Expo Go compatível com SDK 57** e conecte o celular e o computador
à mesma rede Wi-Fi. A versão pode ser consultada no
[site oficial do Expo Go](https://expo.dev/go).

Pare o servidor anterior com `Ctrl+C`, se estiver usando a mesma porta, e execute:

```sh
npx expo start --go --port 8081
```

Leia o QR code no terminal usando o Expo Go no Android ou a câmera do iPhone.
Depois de abrir o projeto, toque em **Criar**. No iPhone, entre com a
mesma conta Expo no aplicativo e na CLI, usando `npx expo login` no computador,
conforme a [orientação oficial do Expo](https://docs.expo.dev/get-started/start-developing/).

Se a rede impedir a conexão, pare o servidor e tente
`npx expo start --go --tunnel`; esse modo depende da internet e pode solicitar
suporte adicional a túnel. Use o novo QR code. `localhost` no celular aponta
para o próprio aparelho, não para o computador.

#### Compilar e instalar no aparelho

Os scripts abaixo compilam o aplicativo nativo; são uma alternativa ao Expo Go.

| Destino | Comando | Pré-requisitos |
| --- | --- | --- |
| Android | `npm run android -- --device` | Android Studio, Android SDK, Java e aparelho com depuração USB autorizada, ou emulador configurado. |
| iPhone | `npm run ios -- --device` | Mac com Xcode, aparelho preparado para desenvolvimento e assinatura configurada. Não compila localmente no Windows. |

Esses scripts executam `expo run:android` e `expo run:ios`, respectivamente.
Podem gerar pastas nativas e ajustar a configuração do projeto. Para detalhes,
consulte [compilação local no Expo](https://docs.expo.dev/guides/local-app-development/).

#### Gerar APK e IPA sem assinatura pelo GitHub Actions

Depois de enviar `.github/workflows/mobile-build.yml` à branch principal, abra
**Actions → Build APK e IPA unsigned → Run workflow**. Selecione a branch,
preencha a URL pública HTTPS da API. Esse valor fica embutido no app; não
informe credenciais. A casa é escolhida após o login.

Ao terminar, baixe `TetoJusto-Android` e `TetoJusto-iOS-unsigned` em
**Artifacts** da execução e extraia os arquivos. Não precisa de `EXPO_TOKEN`,
EAS ou certificados Apple para gerar esses builds.

- O APK usa a configuração Release com a chave de teste padrão do template
  Expo e inclui o JavaScript; funciona sem Metro. Uma instalação anterior
  assinada pelo EAS precisa ser desinstalada antes (isso apaga os dados locais).
- O IPA é para dispositivos iOS e não tem assinatura. Assine-o ao instalar
  com Sideloadly; não é um arquivo para instalação direta ou TestFlight.

O workflow usa [Prebuild do Expo](https://docs.expo.dev/workflow/continuous-native-generation/)
para gerar os projetos nativos e compila nos runners do GitHub. Os dois
builds são independentes: a falha de um não cancela o outro. Os artefatos
ficam disponíveis por 14 dias.

#### Publicar APK e IPA no GitHub Releases

O workflow em `.github/workflows/mobile-release.yml` roda quando uma tag `v*`
é enviada ao GitHub. Ele solicita ao EAS Build um APK Android e um IPA iOS
para distribuição interna e anexa ambos ao Release da mesma tag. O
`src/frontend/app.json` já vincula o projeto à organização `teto-justo-app` e
define `com.tetojusto.app` como identificador Android e iOS. Preserve esses
identificadores para que as próximas versões atualizem o mesmo aplicativo.
Antes da primeira execução automatizada, em `src/frontend`:

1. Use uma conta Apple Developer ativa para o IPA de dispositivo e cadastre os
   iPhones de teste com `npx eas-cli@latest device:create`. Execute
   `npx eas-cli@latest build --platform android --profile release` e depois
   `npx eas-cli@latest build --platform ios --profile release` uma vez no
   computador. Esses comandos interativos configuram as credenciais de
   assinatura no EAS. Confirme que ambos terminam com sucesso antes de usar o
   workflow, que roda sem interação.
2. Crie um token de acesso na [conta Expo](https://expo.dev/settings/access-tokens)
   com permissão para esse projeto. Salve-o no repositório GitHub em
   **Settings → Secrets and variables → Actions** como `EXPO_TOKEN`.
3. Antes de cada versão, atualize `expo.version` em `app.json`. Depois de
   integrar essa configuração à branch principal, na raiz da sua cópia do
   repositório crie uma tag no commit desejado e envie-a, por exemplo,
   `git tag v1.0.0` e
   `git push origin v1.0.0`. Veja a execução em **Actions** e os arquivos em
   **Releases**. Para publicar uma nova versão, crie outra tag.

O IPA interno só pode ser instalado em aparelhos incluídos no perfil de
provisionamento Apple. Para distribuição ampla, use TestFlight/App Store.
Sem as credenciais iOS, o workflow não publica o Release, pois exige que os
builds Android e iOS terminem. O APK pode ser testado separadamente com o
comando de build Android acima.
O login agora obtém a credencial em tempo de execução. Não configure tokens
de sessão no EAS, no GitHub ou em variáveis `EXPO_PUBLIC_*`, pois elas ficam
legíveis no aplicativo distribuído. Configure somente a URL pública da API
(HTTPS em ambientes distribuídos).

Esta mudança não libera o projeto para distribuição pública: ainda há
pendências de autorização por recurso, limitação de tentativas de login e
validação em dispositivos. Veja
[autenticação da sprint 2](./contexto/sprint_2/autenticacao.md).

#### Ver as alterações

Salve os arquivos com o servidor ativo para atualizar a interface. Se necessário,
pressione `r` no terminal ou recarregue a página. Para limpar o cache da prévia
web, pare o servidor e execute `npm run web -- --clear`.

Depois de instalar uma versão nativa, alterações apenas em TypeScript normalmente
precisam somente de `npm start` e da abertura do app instalado. Mudanças em
dependências nativas podem exigir nova compilação. Encerre o servidor com `Ctrl+C`.

O [tutorial detalhado](./contexto/sprint_2/tutorial_execucao_frontend.md) inclui
orientações de conexão e execução no Windows. A validação em aparelhos Android
e iOS ainda está pendente; os resultados já obtidos estão no
[contexto do frontend](./contexto/sprint_2/frontend_tarefas.md).

## Contexto do projeto

A pasta [`contexto/`](./contexto/) reúne resumos técnicos organizados por
sprint. Esses documentos registram o objetivo de cada entrega, os arquivos e
comportamentos alterados, decisões importantes, validações executadas e
pendências reais.

Ao concluir uma alteração no repositório, crie ou atualize o resumo
correspondente em `contexto/sprint_N/`. Prefira um nome curto e descritivo para
o arquivo, como `autenticacao.md` ou `testes_sessao.md`, e evite incluir
credenciais ou outras informações sensíveis.

## Qualidade de código

### Backend: Ruff

O projeto usa o **Ruff** para linting e formatação do código Python. Na pasta
`src/backend`, crie e ative o ambiente virtual caso ainda não o tenha feito:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install ruff
```

> **Nota:** após a ativação, o terminal deve mostrar `(venv)` no início da
> linha.

> **Aviso no PowerShell:** se a ativação do ambiente for bloqueada pela
> política de execução, libere scripts apenas para o terminal atual e tente
> novamente:
>
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
> ```

Com o ambiente ativo, utilize:

```powershell
# Verifica problemas de estilo e código
ruff check .

# Corrige automaticamente o que for possível
ruff check --fix .

# Formata o código
ruff format .
```

As regras estão definidas em `src/backend/ruff.toml`.

### Backend: Bandit (SAST)

O **Bandit** realiza análise estática de segurança no código Python. Instale-o
no ambiente virtual e execute a varredura a partir de `src/backend`:

```powershell
pip install bandit
bandit -r . -x ./venv,./tests
```

O parâmetro `-r` analisa os arquivos recursivamente e `-x` exclui o ambiente
virtual e os testes. Dê atenção especial aos achados com gravidade `High` ou
`Medium` antes de enviar alterações para produção.

### Boas práticas

Antes de criar um commit, siga este fluxo no backend:

1. Execute `ruff check .` para identificar problemas de código.
2. Execute `ruff check --fix .` quando houver correções automáticas
   disponíveis e revise as alterações geradas.
3. Execute `ruff format .` para manter a formatação consistente.
4. Execute `bandit -r . -x ./venv,./tests` para verificar vulnerabilidades
   conhecidas no código Python.
5. Corrija ou avalie os alertas relevantes antes de enviar as alterações.

Para sair do ambiente virtual ao encerrar o trabalho, execute `deactivate`.

### Frontend

Dentro de `src/frontend`, após preparar e iniciar o projeto:

```sh
npm run lint
npx tsc --noEmit
```

O lint global possui pendências de formatação registradas no contexto da
sprint 2; uma falha nessa verificação não significa, por si só, que o servidor
de desenvolvimento não possa iniciar.
