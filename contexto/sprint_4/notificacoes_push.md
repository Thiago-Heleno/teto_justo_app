# Infraestrutura de push — Sprint 4

## Objetivo e arquivos

Disponibilizar cadastro de dispositivos e envio de push para os futuros avisos
de tarefas, mantendo as regras no backend, sem funções SQL, triggers ou novas
dependências.

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

## Validação executada

Comandos executados a partir de `src/backend`:

- `python -m pytest tests -k unitario -q`: **423 aprovados, 31 não selecionados**.
  Os testes novos cobrem autenticação, validação, registro repetido, troca de
  conta, remoção por proprietário, envio para 101 dispositivos, paginação,
  limpeza de inválidos, sucesso parcial e falhas de rede/HTTP/resposta.
- `python -m ruff check schemas/notificacao.py services/notificacao.py routers/usuario.py tests/test_notificacao_unitario.py`:
  aprovado.
- `git diff --check`: aprovado.

A execução inicial dos testes HTTP ficou bloqueada no `socketpair` usado pelo
loop de eventos do `TestClient` no sandbox. Fora desse ambiente restrito, os
testes passaram. A suíte emitiu um aviso de depreciação da combinação atual
Starlette/httpx. Nenhuma dependência foi alterada.

## Limites e pendências

- A migration foi escrita e revisada, mas não aplicada a um banco real. Os
  testes simulados não comprovam as constraints ou os privilégios do SQL.
- Não houve envio real ao Expo nem validação de recebimento em aparelho.
- A geração/registro do token e a chamada de remoção no logout pelo aplicativo
  ainda precisam ser conectadas no frontend.
- Esta etapa remove `DeviceNotRegistered` retornado nos tickets imediatos.
  A consulta posterior de recibos não foi implementada; erros que apareçam
  somente neles não são limpos por este serviço. Tickets aceitos não comprovam
  entrega no aparelho. Ver a [documentação do Expo](https://docs.expo.dev/push-notifications/sending-notifications/).
- O job de avisos, `aviso_enviado_em` e a configuração do cron pertencem à
  próxima etapa.
