# Alinhamento de tarefas e pontuação — Sprint 2

## Objetivo

Unificar o contrato de criação, edição e conclusão de tarefas com o placar.
A integração do rodízio foi reativada no backend e no frontend. O balanceador
atribui cada ocorrência pela pontuação potencial histórica e pelas regras de
elegibilidade. A gravação usa diretamente as tabelas existentes, sem RPC ou
funções SQL. Nenhuma migration foi editada ou executada para essa integração.

## Contrato atual

- `POST /tarefas/` cria uma tarefa `unitaria` com um responsável, peso 1–3,
  `prazo_dias` e `atraso_maximo` entre 1 e 5. Os pontos possíveis são derivados
  do peso: 10, 25 ou 50. `modo_prazo: "intervalo"` inicia na criação e vence após
  `prazo_dias` períodos de 24 horas. `modo_prazo: "dia_fixo"` recebe `data_fixa`
  (data local da casa), vence no fim desse dia e abre `prazo_dias` antes.
- `PATCH /tarefas/{id}` edita as regras permitidas para tarefa unitária; o
  cliente envia `prazo_dias` e, no modo de dia fixo, `data_fixa`. `data_fim` é
  calculada pelo backend e não é aceita como entrada. Datas de instante na
  resposta usam UTC explícito, inclusive para registros legados armazenados
  sem fuso.
- `POST /tarefas/{id}/conclusoes` só pode ser chamado pelo responsável
  atribuído. O desconto é calculado em Python:
  `100 / (atraso_maximo + 1)` por dia de atraso, com arredondamento final. A
  operação transacional registra conclusão, um evento de crédito e o saldo,
  impedindo crédito duplicado inclusive em requisições concorrentes. A resposta
  inclui `concluida_em` e `resultado_pontuacao` com `pontos_possiveis`,
  `pontos_ganhos` e `saldo_atual`. O endpoint `PATCH /tarefas/{id}` com apenas
  `{"estado_atual":"finalizado"}` permanece compatível com clientes anteriores.
  O frontend usa o endpoint dedicado e mostra os dois valores de pontos.
- `pertencer.score` é o saldo vitalício materializado. `GET /casas/{id}/placar`
  soma `score_event` por semana (domingo a sábado), mês e ano correntes no
  fuso IANA da casa; também retorna o acumulado dos eventos. O administrador
  usa `GET /casas/{id}/auditoria-score` para ver diferenças entre eventos e
  saldo antes de uma reconciliação. Novas casas usam `America/Sao_Paulo` por
  padrão e o fuso pode ser configurado na API de casas.
- A API de vínculos aceita somente saldo inicial zero e não oferece edição
  livre do saldo. A exclusão de tarefas e vínculos com créditos é bloqueada
  para preservar o histórico do placar.

O frontend grava tarefas comuns pela API quando ela está configurada, usa os
campos aceitos pelo `PATCH` na edição e exibe o placar. Com a API, a opção
rotativa grava a configuração em `POST /rotatividades/`; sem a API, continua
oferecendo somente uma prévia local com dados fictícios. O endpoint
`POST /jobs/rotatividades`, protegido por `ROTATIVIDADE_JOB_TOKEN`, cria as
ocorrências previstas e atribui seus responsáveis automaticamente. Ele precisa
ser chamado por um agendador externo diariamente.

## Arquivos principais

- `src/backend/schemas/` e `src/backend/routers/`: contratos e endpoints de
  tarefas, casas e vínculos.
- `src/backend/services/tarefa.py` e `placar.py`: janelas, conclusão e agregação
  do placar.
- `src/frontend/src/app/nova-tarefa.tsx`, `tarefas.tsx` e componentes de
  detalhe/edição: criação, placar, conclusão e edição conectadas à API.

## Migrations e histórico

| Arquivo | Papel |
| --- | --- |
| `docs/migrations/14.sql` | Contrato de duração e pontos-base (`pontuacao` derivada da dificuldade, colunas de prazo). |
| `docs/migrations/15.sql` | Remove o trigger de crédito de pontos e sua função de cálculo. |
| `docs/migrations/16.sql` | Cria a função SQL `registrar_conclusao_tarefa`. |
| `docs/migrations/17.sql` | Acrescenta `tipo` e `modo_prazo` à tarefa. |
| `docs/migrations/18.sql` | Converte `score_event.criado_em` para `TIMESTAMPTZ`, cria as tabelas do rodízio, acrescenta `casa.timezone`/`rotacao_versao` e revoga escrita pública em `score_event` e `pertencer`. |
| `docs/migrations/19.sql` | Cria a função SQL `criar_rotatividade`; não é usada pela implementação atual. |
| `docs/migrations/20.sql` | Redeclara `registrar_conclusao_tarefa` (redundante). |
| `docs/migrations/21.sql` | Cria a função SQL `registrar_ocorrencia_rotativa`; não é usada pela implementação atual. |
| `docs/migrations/22.sql` | Cria `excluir_tarefa_sem_credito` e `excluir_vinculo_sem_credito` e os respectivos grants. |
| `docs/migrations/23.sql` | Reconcilia `pertencer.score` com a soma de `score_event`. |
| `docs/migrations/24.sql` | Acrescenta `score_event.tipo` (`credito`/`reversal`) e o índice único parcial do crédito. |
| `docs/migrations/25.sql` | Remove `registrar_conclusao_tarefa`, `excluir_tarefa_sem_credito` e `excluir_vinculo_sem_credito`, já migradas para o backend. |

O esquema de rodízio em `18.sql` é usado pela integração. As funções SQL de
`19.sql` e `21.sql` continuam no banco, mas não são chamadas: criação, seleção
do responsável e gravação da ocorrência são feitas no backend. A integração do
rodízio não editou nem executou nenhuma migration.

Estado do banco: as migrations `14` a `24` foram aplicadas no Supabase em
27–28/09 e a `25` aparece como aplicada no banco de testes na validação de
29/09 (`score.md`). Antes de habilitar o rodízio ou o placar em outro ambiente,
confira o histórico aplicado nele; o rodízio exige as tabelas e colunas de
`18.sql`, e não exige as funções de `19.sql` ou `21.sql`.

## Jobs agendados

O backend não agenda nada sozinho. O serviço `agendador` do
`docker-compose.yml` (Alpine com `crond` e `curl`, horários em
`src/agendador/crontab`) chama os dois endpoints uma vez por dia, às 03:05 UTC
(00:05 em Brasília), usando os tokens do `.env`:

| Endpoint | Cabeçalho / variável | Frequência |
| --- | --- | --- |
| `POST /jobs/penalidades` | `X-Penalidade-Job-Token` / `PENALIDADE_JOB_TOKEN` | Diária, 03:05 UTC. |
| `POST /jobs/rotatividades` | `X-Rotatividade-Job-Token` / `ROTATIVIDADE_JOB_TOKEN` | Diária, 03:05 UTC. |

O agendador deve ficar ligado em uma única máquina, porque o bloqueio do job de
rodízio existe só no processo do backend e o banco é compartilhado. O
`docker-compose.yml` foi validado com `docker compose config`; a execução do
container não foi testada, porque o Docker Desktop estava desligado.

## Validação e pendências

Na integração do rodízio, passaram 267 testes unitários do backend, 24 testes
do frontend, Ruff dos arquivos Python alterados e `git diff --check`. O
typecheck do frontend, o lint completo e um teste do rodízio de ponta a ponta
com o Supabase real não foram executados. Os testes de integração de conclusão,
crédito e concorrência foram executados contra o Supabase de testes
(`concorrencia_retry.md`). A gravação de configuração e a
gravação da ocorrência/atribuição são escritas separadas; o job precisa rodar
em uma única instância ativa até haver uma estratégia de concorrência
distribuída. A validação em Android e iOS também continua pendente.
