# Agendamento de penalidades e rotatividade

## Objetivo

Manter a configuração de agendamento no projeto do backend e usar o Vercel
Cron para disparar os serviços existentes de penalidades e rotatividade,
substituindo o contêiner separado de cron.

## Comportamento

- `src/backend/vercel.json` agenda `GET /jobs/rotatividades` e
  `GET /jobs/penalidades` diariamente com `5 3 * * *` (03:05 UTC, 00:05 em
  Brasília). Os disparos automáticos são realizados pela Vercel em produção.
- Os GETs exigem `Authorization: Bearer <CRON_SECRET>`. Segredo ausente ou
  vazio retorna `503`; autenticação ausente ou inválida retorna `401`, antes
  de obter o cliente do banco ou invocar o serviço. Respostas de sucesso
  usam `Cache-Control: no-store`.
- Os POSTs existentes continuam disponíveis com `PENALIDADE_JOB_TOKEN` /
  `X-Penalidade-Job-Token` e `ROTATIVIDADE_JOB_TOKEN` /
  `X-Rotatividade-Job-Token`. Esses segredos são opcionais para chamadas
  manuais e independentes de `CRON_SECRET`.
- `.env.example` documenta os segredos com valores vazios. O segredo real deve
  ser configurado nas variáveis de Production do projeto do backend.
- Tarefa dentro do prazo permanece `pendente`; após o vencimento fica
  `atrasada`; ao ultrapassar `atraso_maximo`, passa para `nao_feito`.
- Cada alteração compara estado, vencimento e tolerância atuais, de modo que
  execuções concorrentes não sobrescrevam conclusão ou edição concorrente.
- A rotina não debita saldo nem grava eventos de pontuação. A perda proporcional
  `100 / (atraso_maximo + 1)` por dia é refletida no crédito calculado ao
  concluir; a conclusão existente grava o evento uma única vez.
- O GET de rotatividade reaproveita o serviço que cria ocorrências e repara
  tarefas sem atribuição. A unicidade existente evita tarefas repetidas para
  o mesmo rodízio e data; os testes de repetição são sequenciais.
- O serviço `agendador` foi removido do Docker Compose, junto com
  `src/agendador/crontab`. O ambiente local inicia apenas o backend; os jobs
  podem ser chamados manualmente.

## Arquivos

- `src/backend/vercel.json` e `src/backend/routers/jobs.py`: horários e rotas
  GET autenticadas, sem alterar os serviços de negócio nem os schemas.
- `docker-compose.yml` e remoção de `src/agendador/crontab`: retirada do cron
  local separado.
- `.env.example`, `README.md`, `scripts/dev.ps1` e
  `contexto/sprint_3/execucao_local.md`: configuração, ativação na Vercel e
  orientação de execução local.
- `src/backend/tests/test_jobs_router_unitario.py`: autenticação dos dois
  GETs, bloqueio antes do banco, invocação dos serviços e controle de cache.
- `src/backend/tests/test_servico_agendamento_rotatividade_unitario.py`:
  ampliação do teste existente para repetição e reparação de atribuição, com
  banco simulado.

## Decisões e limites

- Nenhuma dependência, migration ou função SQL/RPC foi adicionada. A
  autenticação dos POSTs foi preservada para não quebrar chamadas existentes.
- O projeto da Vercel precisa usar `src/backend` como Root Directory,
  configurar `CRON_SECRET` em Production e fazer um novo deploy. A ativação
  e a execução real na Vercel não foram verificadas.
- No Hobby, cada cron executa no máximo uma vez por dia e pode ser disparado
  dentro da hora configurada. A Vercel não oferece retry automático de falhas,
  e os jobs continuam sujeitos ao tempo máximo da função.
- O `Lock` da rotatividade continua local ao processo e não coordena réplicas.
  A restrição atual de atribuição é por usuário e tarefa: ela não impede dois
  responsáveis diferentes se duas instâncias calcularem atribuições distintas
  simultaneamente. Um bloqueio distribuído permanece pendente; não foi
  acrescentado um serviço externo para esta alteração.

## Validação

- Suíte unitária do backend: 374 testes aprovados, com dois avisos de
  depreciação do TestClient/httpx e AnyIO. Testes de integração foram excluídos
  dessa execução; não houve chamadas ao banco real.
- Ruff: lint e verificação de formatação dos três arquivos Python alterados
  aprovados.
- JSON do cron e parser de `scripts/dev.ps1`: aprovados.
- `git diff --check`: aprovado.
- Testes de integração com Supabase não executados; dependem de um ambiente de
  teste configurado.
- Build/deploy da Vercel e execução do Docker Compose não foram realizados.

## Referências

- [Configuração e produção](https://vercel.com/docs/cron-jobs/quickstart)
- [Autenticação, falhas e concorrência](https://vercel.com/docs/cron-jobs/manage-cron-jobs)
- [Limites por plano](https://vercel.com/docs/cron-jobs/usage-and-pricing)
