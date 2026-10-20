# Notificações push — Sprint 4

## Objetivo e arquivos

Cadastrar dispositivos e emitir avisos normais de atribuição, mudança de prazo
ou responsável, início próximo, rodízio e encerramento do prazo de execução.
O aviso existente de vencimento nas próximas 25 horas é preservado. O app
Android permite ativação no perfil e abre a tarefa ou a lista ao tocar no aviso.

- `docs/migrations/29.sql`: tabela `dispositivo_push`, UUID automático, FK para
  usuário com exclusão em cascata, token único, plataforma Android/iOS,
  criação com fuso e índice por usuário. Acesso direto restrito a `service_role`.
- `src/backend/schemas/notificacao.py`: validação dos tokens Expo e das
  plataformas; resposta de cadastro sem token. Campos extras são recusados.
- `src/backend/routers/usuario.py`: `POST` e `DELETE /usuarios/eu/dispositivos`,
  ambos autenticados por `UsuarioAtual`.
- `src/backend/services/notificacao.py`: cadastro, remoção e `enviar_push`.
- `src/backend/services/usuario.py`: limpeza dos dispositivos na anonimização
  de contas, que não dispara a exclusão em cascata.
- `src/backend/tests/test_notificacao_unitario.py` e
  `src/backend/tests/test_servico_usuario_unitario.py`: cobertura unitária com
  Supabase e HTTP simulados.
- `docs/migrations/30.sql`: marca a tentativa de aviso por tarefa.
- `docs/migrations/31.sql`: marca separadamente a tentativa do aviso de início
  e indexa as tarefas pendentes ainda não processadas.
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

O retorno separa `aceitos` (ID do dispositivo e do ticket), `invalidos` (IDs
dos dispositivos com `DeviceNotRegistered`) e `falhas` (ID do dispositivo e
código genérico). Não inclui tokens nem mensagens de erro externas. Um lote
com falha preserva os resultados dos outros lotes. Não há retry automático,
pois um timeout pode ocorrer depois da aceitação pelo Expo.

Somente `DeviceNotRegistered` provoca remoção. Falhas HTTP, erros individuais
diferentes e respostas malformadas preservam o cadastro. A limpeza também
confere o usuário, preservando um token reassociado a outra conta durante o
envio.

O cron consulta tarefas `pendente` ou `atrasada` cujo `data_fim` está entre o
instante da execução e as próximas 25 horas. Busca os responsáveis em
`atribuida`, marca `aviso_enviado_em` com comparação atômica de estado, prazo e
marcação nula, então envia uma mensagem genérica com `tarefa_id` e `casa_id`.
Repetir o job não duplica o aviso. Mudar o vencimento ou os responsáveis limpa a
marcação para permitir novo aviso. A marcação é feita antes do envio: uma falha
posterior pode perder o aviso, mas não cria duplicatas.

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

## Validação executada

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

- A migration `31.sql` deve ser aplicada depois de `29.sql` e `30.sql`, antes
  de habilitar o novo job. Nenhuma migration foi aplicada ou validada em banco
  real nesta implementação.
- As credenciais Android FCM V1 do projeto Expo ainda precisam ser configuradas
  no EAS. Também é preciso fornecer `GOOGLE_SERVICES_JSON` como variável de
  arquivo do EAS ou caminho local para `google-services.json`; não há chave no
  repositório. Não houve APK, envio real ao Expo ou
  teste de recebimento/toque em aparelho. O push remoto exige build de
  desenvolvimento ou release, não funciona no Expo Go.
- O cron gratuito da Vercel roda no máximo uma vez ao dia e pode atrasar até
  uma hora. A janela de início é de 24 horas: tarefas criadas depois da
  execução ou com início entre duas execuções podem ficar sem esse lembrete.
  O aviso não é garantido exatamente 24 horas antes do início.
- As marcações registram tentativas, não entrega confirmada. Falhas depois
  da reserva podem perder o aviso; não há retry automático nem fila persistente.
  Eventos em segundo plano também podem ser perdidos se o processo encerrar.
- Esta etapa remove `DeviceNotRegistered` retornado nos tickets imediatos.
  A consulta posterior de recibos não foi implementada; erros que apareçam
  somente neles não são limpos por este serviço. Tickets aceitos não comprovam
  entrega no aparelho. Ver a [documentação do Expo](https://docs.expo.dev/push-notifications/sending-notifications/).
- Os botões interativos na própria notificação não foram adicionados. As
  categorias do Expo permitem implementá-los sem assinatura paga do Expo; iOS
  exigirá credenciais de uma conta Apple Developer paga.
