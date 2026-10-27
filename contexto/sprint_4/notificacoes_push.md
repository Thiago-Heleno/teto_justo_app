# Notificações push — Sprint 4

Para configurar Firebase/FCM, fornecer credenciais ao build Android ou testar
push em um APK, siga [Configuração FCM pelo GitHub Actions](#configuração-fcm-pelo-github-actions).

## Objetivo e arquivos

Cadastrar dispositivos e emitir avisos normais de atribuição, mudança de prazo
ou responsável, início próximo, rodízio e encerramento do prazo de execução.
O app Android permite ativação no perfil e abre a tarefa ou a lista ao tocar
no aviso. Os lembretes de vencimento no dia e de atraso ainda tolerado oferecem
as ações Concluir e Ver tarefa.

- `docs/migrations/29.sql`: tabela `dispositivo_push`, UUID automático, FK para
  usuário com exclusão em cascata, token único, plataforma Android/iOS,
  criação com fuso e índice por usuário. Acesso direto restrito a `service_role`.
- `src/backend/schemas/notificacao.py`: validação dos tokens Expo e das
  plataformas; resposta de cadastro sem token. Campos extras são recusados.
- `src/backend/routers/usuario.py`: `POST` e `DELETE /usuarios/eu/dispositivos`,
  ambos autenticados por `UsuarioAtual`.
- `src/backend/services/notificacao.py`: cadastro, remoção, envio e consulta de recibos.
- `src/backend/services/usuario.py`: limpeza dos dispositivos na anonimização
  de contas, que não dispara a exclusão em cascata.
- `src/backend/tests/test_notificacao_unitario.py` e
  `src/backend/tests/test_servico_usuario_unitario.py`: cobertura unitária com
  Supabase e HTTP simulados.
- `docs/migrations/30.sql`: marca a tentativa de aviso por tarefa.
- `docs/migrations/31.sql`: marca separadamente a tentativa do aviso de início
  e indexa as tarefas pendentes ainda não processadas.
- `docs/migrations/32.sql`: marca separadamente a tentativa do aviso de atraso.
- `src/backend/services/tarefa.py` e `src/backend/services/penalidade.py`:
  conectam os eventos aos avisos após as operações confirmadas.
- `src/backend/routers/tarefa.py`: fornece `BackgroundTasks` aos serviços para
  executar notificações após a resposta HTTP.
- `src/backend/routers/jobs.py` e `src/backend/vercel.json`: job diário
  `GET /jobs/notificacoes`, às 03:05 UTC, e novo
  `GET /jobs/notificacoes-avisos`, às 03:15 UTC, protegidos por `CRON_SECRET`.
- `src/frontend/src/services/notificacoes.ts`: permissão, canal Android padrão,
  token Expo, registro, remoção e abertura autenticada da tarefa.
- `src/frontend/app.config.js`: aceita `GOOGLE_SERVICES_JSON` como caminho do
  arquivo Firebase no build Android, sem guardar credenciais no Git.
- `src/frontend/src/components/perfil.tsx` e telas de tarefas: botão de ativação
  e abertura do detalhe a partir do push.

## Contratos e decisões

O `POST` recebe `token` e `plataforma` (`android` ou `ios`). O proprietário é
sempre o usuário autenticado. Retorna `200` com `id`, `plataforma` e `criado_em`,
tanto no primeiro cadastro quanto nas repetições. O upsert usa conflito em
`token`, sem enviar os campos gerados `id` e `criado_em`. Se outra conta
registrar o mesmo token, o vínculo passa para a conta atual.

O `DELETE` recebe somente `token` no corpo JSON e filtra pelo token e usuário
autenticado. Retorna `204`, inclusive se o registro já não existir. O aplicativo
deve chamar essa rota antes de `POST /sessoes/logout`, enquanto a sessão ainda
é válida; sair de um aparelho não remove os demais.

`ServicoNotificacao(supabase).enviar_push(ids_usuarios, titulo, mensagem, dados=None)`
consulta os dispositivos em páginas ordenadas e envia uma mensagem por token,
em lotes sequenciais de até 100, usando `httpx` e timeout de 10 segundos. Todas
as páginas são carregadas antes da limpeza para não pular dispositivos ao
excluir registros. Usuários sem dispositivos não geram requisição ao Expo.

O retorno separa `aceitos` (IDs do dispositivo, do usuário original e do ticket), `invalidos` (IDs
dos dispositivos com `DeviceNotRegistered`) e `falhas` (ID do dispositivo e
código genérico). Não inclui tokens nem mensagens de erro externas. Um lote
com falha preserva os resultados dos outros lotes. Não há retry automático,
pois um timeout pode ocorrer depois da aceitação pelo Expo.

Somente `DeviceNotRegistered` provoca remoção. Falhas HTTP, erros individuais
diferentes e respostas malformadas preservam o cadastro. A limpeza também
confere o usuário, preservando um token reassociado a outra conta durante o
envio.

### Consulta posterior de recibos — 27/10/2026

`POST /jobs/notificacoes-recibos` reutiliza a autenticação dos jobs internos:
`Authorization: Bearer <CRON_SECRET>`. Sem configuração responde `503`; sem
autorização válida, `401`, antes de acessar o banco ou o Expo. A resposta
autorizada usa `Cache-Control: no-store`.

O corpo contém `tickets`, com 1 a 1000 itens no formato de `aceitos` retornado
por `enviar_push`. Cada item tem `dispositivo_id`, `usuario_id` e `ticket_id`,
todos UUIDs. Campos extras e tickets repetidos são recusados com `422`.
O operador deve preservar a associação original; não deve consultar o usuário
atual do dispositivo para preencher um ticket antigo.

O serviço consulta `https://exp.host/--/api/v2/push/getReceipts`, em lotes de
até 1000 IDs e timeout de 10 segundos. Correlaciona resultados pelo ticket,
independentemente da ordem da resposta, e ignora IDs não solicitados. Retorna:

- `confirmados`: recibos `ok`, que confirmam aceitação pelo FCM/APNs;
- `invalidos`: recibos `DeviceNotRegistered`; a limpeza filtra simultaneamente
  pelo ID do dispositivo e pelo usuário do envio original. Cadastros
  reassociados ou recriados são preservados;
- `pendentes`: tickets ausentes da resposta, disponíveis para nova consulta;
- `falhas`: consulta, recibo ou limpeza não confirmados. Erros conhecidos usam
  `MessageTooBig`, `MessageRateExceeded`, `MismatchSenderId` ou
  `InvalidCredentials`; outros recebem códigos genéricos. Mensagens externas
  e tokens de push não são retornados.

Consultar novamente não reenvia notificações. Falhas de um lote ou da limpeza
de um dispositivo não descartam os demais resultados. O chamador pode reutilizar
os identificadores retornados em `pendentes` e `falhas`, retirando `erro` destes
últimos, para repetir somente a consulta ou limpeza necessária.

A consulta é sob demanda: os envios normais e os jobs existentes não armazenam
os tickets nem disparam essa rota. Não foram adicionados fila, agendamento,
migration ou dependência. O chamador interno precisa conservar os tickets e
acionar a consulta. Segundo o [contrato do Expo](https://docs.expo.dev/push-notifications/sending-notifications/#check-push-receipts-for-errors),
é recomendado consultar após cerca de 15 minutos; os recibos são descartados
após 24 horas. Mesmo `ok` não garante exibição no aparelho.

Alterados `src/backend/services/notificacao.py`,
`src/backend/schemas/notificacao.py`, `src/backend/routers/jobs.py` e
`src/backend/tests/test_notificacao_unitario.py`. Os testes são unitários, com
Supabase e Expo simulados.

### Compatibilidade da edição de responsáveis — 27/10/2026

O check de integração reportado falhou com `500` ao trocar o responsável por
um morador válido. A edição escrevia `aviso_atraso_enviado_em` mesmo quando a
coluna ainda não existia. Uma consulta local sem leitura de linhas confirmou
o erro PostgREST `42703` para essa coluna; o estado do banco do CI não foi
consultado. Um teste unitário reproduziu a falha antes da correção.

`src/backend/services/tarefa.py` agora reinicia a marca de atraso somente se
ela estiver presente no registro bruto da tarefa, obtido com `select("*")`.
A marca de vencimento continua sendo reiniciada. Não há captura genérica de
erros nem alteração de permissões. Atualizado
`src/backend/tests/test_servico_tarefa_unitario.py` para verificar a troca de
responsável com e sem a coluna. A migration `32.sql` continua necessária para
o funcionamento completo do job de avisos de atraso; nenhuma migration foi
aplicada nesta tarefa.

### Validação do backend — 27/10/2026

- Antes da correção, o teste de regressão unitário passou com a coluna e falhou
  sem ela, reproduzindo o erro `42703`. Depois, os 106 testes unitários do serviço
  de tarefas passaram.
- A partir de `src/backend`, usando o Python de `.venv`:
  `..\..\.venv\Scripts\python.exe -m pytest -q tests --ignore-glob='*_integracao.py'`:
  **573 aprovados**, com dois avisos de depreciação do TestClient/AnyIO.
- A suíte de notificações e jobs passou com **120 aprovados**. A ausência local
  de `tzdata` causou três falhas na execução anterior à mudança; instalada a versão
  `2025.3`, já declarada em `requirements.txt`, sem alterar o manifesto.
- Ruff nos seis arquivos Python alterados e `git diff --check`, a partir da
  raiz: aprovados.
- Sem testes de integração contra banco real, build ou envio/consulta real ao
  Expo. O check de integração do GitHub ainda precisa ser reexecutado.

### Avisos de vencimento e atraso

O cron busca tarefas `pendente` ou `atrasada` com vencimento futuro nas próximas
36 horas e filtra pelo dia atual no fuso da casa. Não avisa tarefas cujo início
ainda está no futuro. Para as vencidas, avisa quando os dias de atraso calculados
pelo serviço de score estão entre 1 e `atraso_maximo`, inclusive. Busca os
responsáveis em `atribuida` e reserva separadamente `aviso_enviado_em` ou
`aviso_atraso_enviado_em`, comparando estado, prazo e marcação nula antes do envio.
Repetir o job não duplica o mesmo aviso. A marcação registra tentativa: uma falha
posterior pode perder o aviso. Os payloads usam `tarefa_vence_hoje` ou
`tarefa_atrasada`, com `tarefa_id`, `casa_id` e categoria `tarefa_pendente`.

O layout do app registra os botões Concluir e Ver tarefa para essa categoria.
As duas ações abrem o app e verificam sessão, casa e tarefa. Concluir chama
`POST /tarefas/{id}/conclusoes` e depois abre o detalhe; se a conclusão falhar,
o detalhe também é aberto para conferência. Ver tarefa e o toque normal abrem
o detalhe. A apresentação e a execução desses botões em aparelho continuam sem
validação documentada.

### Eventos de notificação normal

- Criação: avisa os responsáveis depois de confirmar a tarefa e suas
  atribuições. Falhas anteriores não agendam notificações.
- Edição: compara datas normalizadas e conjuntos de responsáveis. Reenviar
  os mesmos dados não gera aviso normal. Novos responsáveis recebem a
  atribuição; os removidos recebem a retirada; quem continua recebe a mudança
  de prazo, quando houver. Mudar prazo e responsável na mesma edição não
  envia avisos redundantes ao novo responsável.
- Encerramento: a transição confirmada para `nao_feito`, tanto no job de
  penalidades quanto na sincronização durante uma consulta, agenda um aviso
  de prazo encerrado. Repetir a consulta/job ou perder a disputa pela atualização
  não repete esse evento. A mensagem não afirma que houve débito de pontos,
  porque o job existente apenas altera o estado.
- Os eventos das rotas usam `BackgroundTasks`. A preparação e o envio capturam
  falhas com mensagens genéricas, sem expor erros externos ou tokens. Uma
  falha do push não altera o resultado da operação principal.

### Avisos de início e resumo do rodízio

O novo job consulta tarefas `pendente`, com `data_inicio` maior que o instante
atual e menor ou igual às próximas 24 horas, cujo `aviso_inicio_tentado_em`
está nulo. Tarefas sem responsável não são reservadas. Todas as páginas são
carregadas antes de marcar as tentativas.

A reserva compara ID, início, estado pendente e marcação nula em uma atualização.
Somente a execução que consegue reservar envia o aviso. O controle é independente
de `aviso_enviado_em`, usado pelo aviso de vencimento.

Tarefas unitárias recebem o aviso `inicio_tarefa`. Ocorrências do rodízio são
agrupadas por usuário e casa, em um único resumo `rodizio_distribuido`, que
substitui o aviso individual de início dessas ocorrências. O resumo considera
somente a janela de início; não avisa sobre os 60 dias gerados antecipadamente.

Alterar efetivamente o início ou os responsáveis agenda a limpeza da marca de
início em segundo plano. Essa atualização confere o início atual e o estado
pendente; uma falha nela não impede salvar a edição da tarefa. Alterar apenas
o vencimento, mantendo o início e o responsável, não reinicia esse aviso.

Os payloads normais usam `tipo`, `casa_id` e, nos avisos individuais, `tarefa_id`.
Não possuem categoria de botões interativos. O resumo do rodízio abre a lista
somente após verificar a sessão e o acesso à casa, sem consultar uma tarefa
individual. Os demais avisos mantêm a abertura do detalhe existente.

No Android, o usuário ativa os avisos pelo perfil. O token é cadastrado em
`POST /usuarios/eu/dispositivos` e removido em `DELETE` antes do logout. Ao
reiniciar com sessão válida, o app atualiza o cadastro se o token mudou. Um
toque consulta a tarefa pela API autenticada, troca para sua casa se necessário
e abre o detalhe; se a tarefa não existir ou não for acessível, abre a lista.

## Configuração FCM pelo GitHub Actions

### Estado e arquivos necessários

Guia revisado em 27/10/2026. O fluxo existente é **backend → Expo Push
Service → FCM → Android**. O app já solicita permissão, cria o canal Android
e registra o `ExpoPushToken` pela API. O backend envia pelo Expo, sem SDK
Firebase ou credencial Google no servidor.

O passo de preparação Firebase foi acrescentado ao workflow manual
`.github/workflows/mobile-build.yml`, no mesmo nível dos demais passos e antes
do Prebuild. O bloqueio de indentação da revisão de 25/10/2026 já foi corrigido.
As contas externas, os secrets e a entrega em aparelho não foram verificados.

| Item | Onde fornecer e para quê |
| --- | --- |
| `google-services.json` | Conteúdo completo no secret `GOOGLE_SERVICES_JSON` do GitHub; configura o Firebase no APK. Contém identificadores públicos, legíveis no app. |
| JSON da conta de serviço | Upload nas credenciais FCM V1 do projeto Expo/EAS; contém chave privada e fica fora do APK, Git, logs e documentação. |
| Identificadores Firebase | Conferir `project_id` e o projeto/número remetente da configuração Android contra o projeto autorizado pela conta de serviço. Usar o mesmo projeto neste fluxo. |
| Projeto Expo e pacote Android | Preservar o projeto `teto-justo`, da organização `teto-justo-app`, e o pacote `com.tetojusto.app`, já configurados no app. |
| `ExpoPushToken` | O app obtém e cadastra automaticamente para o usuário autenticado; não é um token fixo para configurar no build. |
| `EXPO_TOKEN` | Autentica o workflow separado de releases via EAS; não é necessário para compilar no workflow manual escolhido. |

Os dois JSONs têm funções diferentes: somente o `google-services.json` entra
no build. A chave privada deve ser enviada diretamente ao EAS, sem colar seu
conteúdo em chat ou usá-la como variável `EXPO_PUBLIC_*`.

### 1. Cadastrar o aplicativo Android no Firebase

No [Firebase Console](https://console.firebase.google.com/), criar ou selecionar
o projeto da equipe. Em **Visão geral do projeto → Adicionar app → Android**,
registrar o pacote **`com.tetojusto.app`** e baixar `google-services.json`.
Se o aplicativo já estiver cadastrado, baixar o arquivo em **Configurações do
projeto → Geral → Seus aplicativos → Android**.

Concluir quando existir um cliente no JSON com
`client_info.android_client_info.package_name` igual ao pacote do app. Esse
arquivo deve ter a configuração Android, sem o campo `private_key` da conta
de serviço. O Expo Prebuild fará a integração nativa; este guia não exige
editar Gradle manualmente. Ver [cadastro Android no Firebase](https://firebase.google.com/docs/android/setup).

### 2. Preparar a credencial de envio FCM V1

Em **Configurações do projeto → Cloud Messaging**, conferir que a Firebase
Cloud Messaging API (V1) está habilitada. Se necessário, usar **Gerenciar API
no Google Cloud Console** para habilitá-la no mesmo projeto.

Em **Configurações do projeto → Contas de serviço → Firebase Admin SDK →
Gerar nova chave privada**, baixar o JSON e guardá-lo fora do repositório.
No [Google Cloud Console](https://console.cloud.google.com/), em **IAM e
administrador → IAM**, localizar a conta pelo `client_email` do arquivo e
conferir a permissão de envio; a função **Firebase Cloud Messaging API Admin**
(`roles/firebasecloudmessaging.admin`) permite esse envio. A equipe precisa
de acesso para gerenciar a API, as permissões e as chaves dessa conta.

Concluir quando a API estiver habilitada e a conta estiver autorizada no
projeto Android. Usar FCM HTTP V1; a antiga server key não substitui essa
credencial. Referências: [autorização FCM V1](https://firebase.google.com/docs/cloud-messaging/send/v1-api)
e [credenciais FCM no Expo](https://docs.expo.dev/push-notifications/fcm-credentials/).

### 3. Cadastrar a conta de serviço no Expo

Acessar as [credenciais do projeto Teto Justo](https://expo.dev/accounts/teto-justo-app/projects/teto-justo/credentials)
com permissão para gerenciá-las. A navegação parte de **Project settings**;
**Organization settings** é a configuração da organização e não contém essa tela.
Abrir **Credentials → Android → com.tetojusto.app → Service credentials → FCM V1 service account
key → Add a service account key**. Em **Upload new key**, enviar o JSON da
conta de serviço e salvar.

Concluir quando a credencial FCM V1 estiver associada ao identificador Android
correto. O EAS armazena a credencial de envio mesmo quando o GitHub compila o
APK sem EAS Build. Ver [upload da credencial no Expo](https://docs.expo.dev/push-notifications/fcm-credentials/).

Se a segurança adicional de push estiver habilitada no painel Expo, o backend
atual precisará enviar um access token Expo no cabeçalho `Authorization`.
Esse suporte não existe no envio atual: registrar essa pendência antes de
testar nesse cenário. A chave Google não substitui esse access token.
Ver [segurança adicional do Expo Push Service](https://docs.expo.dev/push-notifications/sending-notifications/#additional-security).

### 4. Fornecer a configuração ao GitHub Actions

No repositório GitHub, abrir **Settings → Secrets and variables → Actions →
New repository secret**. Nome: `GOOGLE_SERVICES_JSON`. Valor: o conteúdo
completo do `google-services.json`, em JSON original, sem Base64. É necessário
acesso para cadastrar secrets do repositório. Ver [secrets no GitHub Actions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets).

O passo **Prepare Firebase config for Android** está em
`.github/workflows/mobile-build.yml`, antes de **Generate native project**.
Manter esse workflow como fonte do script, no mesmo nível dos demais passos
de `jobs.build.steps`.

No GitHub, o secret contém o **texto JSON**. Nos passos seguintes do job, a
variável `GOOGLE_SERVICES_JSON` contém o **caminho do arquivo** temporário.
`src/frontend/app.config.js` já usa esse caminho em `android.googleServicesFile`.
O script não imprime o JSON e sua condição limita a execução ao Android.
O arquivo precisa existir antes do Prebuild para ser incluído no APK.

Concluir quando o YAML da branch selecionada for válido, a preparação ocorrer
antes do Prebuild e o secret existir. A ausência do secret deve falhar com a
mensagem explícita; após validar o YAML, o job iOS permanece independente
da configuração Android.

Esse secret pertence ao GitHub Actions. O fluxo separado
`.github/workflows/mobile-release.yml` solicita builds ao EAS e não transfere
esse arquivo aos servidores Expo. Para usar Firebase nessa distribuição,
fornecer `GOOGLE_SERVICES_JSON` como variável de arquivo no ambiente EAS usado
pelo perfil `release`; o cadastro da chave FCM V1 autoriza o envio e não fornece
a configuração Android ao build. Ver [variáveis de ambiente no EAS](https://docs.expo.dev/eas/environment-variables/).

### 5. Gerar o APK e verificar o recebimento

Abrir **Actions → Build APK e IPA unsigned → Run workflow**, selecionar a
branch atualizada e informar a URL pública HTTPS da
API. Baixar **Artifacts → TetoJusto-Android**, extrair e instalar o APK em um
Android com Google Play Services. O APK inclui JavaScript e dispensa Metro.
A mudança de configuração Firebase exige um novo build; Expo Go não oferece
push remoto Android nesta versão do SDK. Ver [configuração de push no Expo](https://docs.expo.dev/push-notifications/push-notifications-setup/).

Se a instalação anterior tiver assinatura diferente, será necessário
desinstalá-la antes, apagando os dados locais. Em seguida:

1. Conferir com a equipe que as migrations `29.sql`, `30.sql`, `31.sql` e `32.sql` foram
   aplicadas nessa ordem e que o backend com notificações está disponível.
2. Entrar no APK, selecionar uma casa e ativar notificações no perfil,
   concedendo a permissão Android. Confirmar sucesso de
   `POST /usuarios/eu/dispositivos` e o vínculo ao usuário, sem divulgar o token.
3. Atribuir uma nova tarefa ao usuário de teste. Confirmar o aviso com o app
   aberto; repetir com uma nova tarefa e o app em segundo plano, sem forçar
   sua parada nas configurações Android.
4. Tocar no aviso e confirmar abertura da tarefa na casa correta. Conferir
   também o toque com o app encerrado normalmente. Sair da conta e confirmar
   que o dispositivo deixa de receber avisos dessa conta.
5. Para lembretes agendados, conferir `CRON_SECRET` no backend e os jobs da
   Vercel. O evento de atribuição acima testa o envio sem esperar o cron.

Concluir a configuração funcional somente após observar recebimento e abertura
em aparelho. Um ticket aceito confirma recebimento pelo Expo, não entrega ao
Android. O operador interno pode preservar os itens de `aceitos` do envio e
usar a [consulta posterior de recibos](#consulta-posterior-de-recibos--27102026).
Não há consulta automática dos envios normais nem garantia de exibição no aparelho.

### Diagnóstico por etapa

| Sintoma | Conferência |
| --- | --- |
| Falha no passo de preparação | Secret `GOOGLE_SERVICES_JSON` no repositório da execução e passo de preparação na branch selecionada. |
| Falha no Prebuild ou na obtenção do token | JSON Android correto, pacote correspondente e APK recompilado com o arquivo. |
| Erro de autorização/credenciais ou remetente | Credencial FCM V1 do Expo, API habilitada, permissão da conta e mesmo projeto Firebase. Conferir o recibo quando o ticket for aceito. |
| Expo retorna `UNAUTHORIZED` | Segurança adicional de push exige autenticação ainda ausente no backend. |
| Cadastro existe, mas o aviso não aparece | Permissão e canal Android, configuração de bateria/rede e recibo Expo; cadastro e ticket não comprovam entrega. |

## Atualização documental — 27/10/2026

- Conferidos `src/backend/services/notificacao.py`,
  `src/frontend/src/app/_layout.tsx`, `src/frontend/src/services/notificacoes.ts`
  e `.github/workflows/mobile-build.yml`.
- Corrigidas as descrições dos lembretes de vencimento e atraso, da categoria
  `tarefa_pendente` e das ações Concluir e Ver tarefa já presentes no código.
- Removido o bloqueio de workflow das orientações atuais; a revisão abaixo é
  histórica e seu erro de indentação já foi corrigido no arquivo atual.
- Mantidas as pendências reais de configuração externa e validação em aparelho.
- Validação a partir da raiz: PyYAML leu o workflow e confirmou a preparação
  Firebase antes do Prebuild; `git diff --check` passou. Nenhum teste da aplicação,
  build ou envio real foi executado nesta etapa exclusivamente documental.

## Revisão histórica dos workflows FCM — 25/10/2026

O bloqueio descrito nesta revisão foi corrigido no workflow atual.

- Base: alterações locais em relação a `32f9b67`, restritas ao workflow manual,
  README e este contexto. Os outros workflows foram lidos como contexto.
- **Bloqueio:** o novo `- name: Prepare Firebase config for Android` está
  indentado dentro do passo anterior. PyYAML rejeitou `mobile-build.yml` com
  `mapping values are not allowed here`. Alinhar esse item com os demais passos
  e validar o YAML antes de iniciar qualquer build; o erro impede ambos os jobs.
  Esta revisão preservou o workflow enviado pelo usuário.
- Os YAMLs `analise-estatica.yml`, `backend-pytest.yml` e `mobile-release.yml`
  foram analisados com PyYAML sem erro de sintaxe. Isso não valida execução
  de actions, credenciais, runners ou ferramentas externas.
- Para verificar a intenção do passo inválido, a indentação foi ajustada
  somente em memória. O script extraído passou em `bash -n` (Git Bash).
  Execução com dados fictícios confirmou falha para secret vazio, preservação
  literal do JSON multilinha e caracteres de shell, caminho com espaços,
  exportação para `GITHUB_ENV` e ausência do JSON nos logs.
- Node confirmou que `app.config.js` aceita o caminho exportado, preserva
  pacote Android, projeto Expo, plugin de notificações e configuração iOS;
  sem a variável, preserva a configuração original.
- O secret GitHub não configura o fluxo EAS de release. A existência de uma
  variável de arquivo no ambiente remoto não foi consultada.
- Revisões paralelas: Standards identificou o estado documental desatualizado
  e a cópia do script; ambos foram resolvidos e reconferidos. Spec identificou
  o bloqueio de indentação acima, ainda pendente. Links locais, âncoras do guia
  e `git diff --check` foram validados sem erro.
- Sem build, aplicação de migrations, envio real ou teste em aparelho.
  Credenciais e secrets externos continuam sem validação independente.

## Validação histórica do guia — 24/10/2026

Os resultados desta seção foram registrados na atualização documental anterior.

- Conferidos o código de registro/envio, a configuração Expo e os workflows
  existentes, além das referências oficiais vinculadas ao guia.
- Exemplo YAML analisado com PyYAML e shell aprovado em `bash -n` (Git Bash).
  Execução local com dados fictícios confirmou falha para secret vazio,
  preservação literal do JSON com quebras de linha e caracteres de shell,
  caminho com espaços, exportação para `GITHUB_ENV` e ausência do JSON nos logs.
- Verificação com Node confirmou que `app.config.js` aceita o caminho exportado
  e preserva as demais configurações. Conferido o link local do README.
- `git diff --check`: aprovado. Somente este contexto e o README foram alterados;
  o exemplo não foi aplicado ao workflow. Sem build, configuração externa ou
  teste em aparelho; as suítes da aplicação não foram reexecutadas.

## Validações históricas da implementação

Os resultados abaixo foram registrados na implementação anterior e não foram
reexecutados nesta atualização documental.

Comandos executados a partir de `src/backend`:

- `python -m pytest tests -k unitario -q`: **481 aprovados, 31 não selecionados**.
  Inclui os fluxos existentes, os limites da janela de 24 horas, paginação,
  reserva concorrente, resumo por usuário/casa, edição sem mudança, falhas de
  gravação e envio, isolamento das notificações e preservação do aviso de
  vencimento. Supabase e Expo são simulados; não são testes de integração real.
- `python -m ruff check` nos arquivos Python alterados: aprovado.
- Em `src/frontend`, suíte definida no script `test:tarefas`, executada
  diretamente com Node 24: **64 aprovados**. Inclui abertura do resumo, sessão
  trocada, casa inacessível, ativação, logout e os demais fluxos de tarefas.
- Em `src/frontend`, `node node_modules/typescript/bin/tsc --noEmit`: aprovado.
- ESLint de `src/frontend/src/services/notificacoes.ts` e Prettier dos dois
  arquivos frontend alterados: aprovados.
- `git diff --check`: aprovado.

A execução inicial dos testes HTTP ficou bloqueada no `socketpair` usado pelo
loop de eventos do `TestClient` no sandbox. Fora desse ambiente restrito, os
testes passaram. A suíte emitiu um aviso de depreciação da combinação atual
Starlette/httpx. O projeto já usa `expo-notifications` compatível com Expo 57;
nenhuma dependência nova foi acrescentada ao manifesto nesta etapa. A instalação
local do frontend foi sincronizada com `npm ci --ignore-scripts --no-audit --no-fund`,
a partir de `src/frontend`, sem alterar o manifesto ou o lockfile. Os testes
de frontend usaram Node 24, pois o Node global disponível não suporta o runner
configurado no projeto.

## Limites e pendências

- As migrations `31.sql` e `32.sql` devem ser aplicadas depois de `29.sql` e
  `30.sql`, antes de habilitar os respectivos avisos. Nenhuma migration foi
  aplicada nesta implementação; a ausência local da coluna de `32.sql` foi
  confirmada apenas por consulta sem leitura de linhas.
- A configuração externa e o teste real continuam pendentes de confirmação.
  Seguir [Configuração FCM pelo GitHub Actions](#configuração-fcm-pelo-github-actions).
  O passo Firebase já está alinhado aos demais passos do workflow. Nenhum APK
  ou envio real foi realizado nesta revisão documental.
- O cron gratuito da Vercel roda no máximo uma vez ao dia e pode atrasar até
  uma hora. A janela de início é de 24 horas: tarefas criadas depois da
  execução ou com início entre duas execuções podem ficar sem esse lembrete.
  O aviso não é garantido exatamente 24 horas antes do início.
- As marcações registram tentativas, não entrega confirmada. Falhas depois
  da reserva podem perder o aviso; não há retry automático nem fila persistente.
  Eventos em segundo plano também podem ser perdidos se o processo encerrar.
- `DeviceNotRegistered` é tratado nos tickets imediatos e na consulta posterior
  sob demanda. Não existe armazenamento ou consulta automática dos tickets dos
  envios normais. Tickets aceitos e recibos `ok` não comprovam exibição no
  aparelho. Ver a [documentação do Expo](https://docs.expo.dev/push-notifications/sending-notifications/).
- Os botões Concluir e Ver tarefa já estão implementados para os lembretes de
  vencimento no dia e atraso; falta confirmar seu funcionamento em aparelho.
