# Notificações push de vencimento — Sprint 4

## Objetivo e arquivos

Cadastrar dispositivos e avisar responsáveis por tarefas que vencem nas próximas
25 horas. O app Android permite ativação no perfil e abre a tarefa ao tocar no
aviso.

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
- `src/backend/routers/jobs.py` e `src/backend/vercel.json`: job diário
  `GET /jobs/notificacoes`, protegido por `CRON_SECRET`, às 03:05 UTC.
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

No Android, o usuário ativa os avisos pelo perfil. O token é cadastrado em
`POST /usuarios/eu/dispositivos` e removido em `DELETE` antes do logout. Ao
reiniciar com sessão válida, o app atualiza o cadastro se o token mudou. Um
toque consulta a tarefa pela API autenticada, troca para sua casa se necessário
e abre o detalhe; se a tarefa não existir ou não for acessível, abre a lista.

## Validação executada

Comandos executados a partir de `src/backend`:

- `python -m pytest tests -k unitario -q`: **453 aprovados, 31 não selecionados**.
  Inclui janela de 25 horas, tarefa encerrada, destinatário, repetição e falha
  de envio, além dos cenários anteriores de dispositivo e HTTP simulado.
- `python -m ruff check` nos arquivos Python alterados: aprovado.
- `npm run test:tarefas` em `src/frontend`: **62 aprovados**, incluindo ativação,
  permissão negada, logout e toque no aviso.
- `npx tsc --noEmit` e ESLint nos arquivos TypeScript alterados: aprovados.
- `npx expo export --platform android --output-dir dist` e exportação web:
  aprovados. A exportação Android valida o bundle JavaScript, não gera APK.
- `git diff --check`: aprovado.

A execução inicial dos testes HTTP ficou bloqueada no `socketpair` usado pelo
loop de eventos do `TestClient` no sandbox. Fora desse ambiente restrito, os
testes passaram. A suíte emitiu um aviso de depreciação da combinação atual
Starlette/httpx. `expo-notifications` foi adicionado na versão compatível com o
Expo 57.

## Limites e pendências

- As migrations `29.sql` e `30.sql` precisam ser aplicadas nessa ordem no banco
  usado pela API. Não foram aplicadas nem validadas em banco real.
- As credenciais Android FCM V1 do projeto Expo ainda precisam ser configuradas
  no EAS. Também é preciso fornecer `GOOGLE_SERVICES_JSON` como variável de
  arquivo do EAS ou caminho local para `google-services.json`; não há chave no
  repositório. Não houve APK, envio real ao Expo ou
  teste de recebimento/toque em aparelho. O push remoto exige build de
  desenvolvimento ou release, não funciona no Expo Go.
- O cron gratuito da Vercel roda no máximo uma vez ao dia e pode atrasar até
  uma hora. Tarefas criadas pouco antes do prazo podem não receber aviso.
- Esta etapa remove `DeviceNotRegistered` retornado nos tickets imediatos.
  A consulta posterior de recibos não foi implementada; erros que apareçam
  somente neles não são limpos por este serviço. Tickets aceitos não comprovam
  entrega no aparelho. Ver a [documentação do Expo](https://docs.expo.dev/push-notifications/sending-notifications/).
- Os botões interativos na própria notificação não foram adicionados. As
  categorias do Expo permitem implementá-los sem assinatura paga do Expo; iOS
  exigirá credenciais de uma conta Apple Developer paga.
