# Alinhamento de tarefas, rodízio e pontuação — Sprint 2

## Objetivo

Unificar o contrato de criação, edição e conclusão de tarefas com o placar e a
geração de ocorrências rotativas. As migrations antigas permanecem intactas;
suas descrições em outros documentos da sprint registram o comportamento de
cada entrega na época.

## Contrato atual

- `POST /tarefas/` cria uma tarefa `unitaria` com um responsável, peso 1–3,
  `prazo_dias` e `atraso_maximo` entre 1 e 5. Os pontos possíveis são derivados
  do peso: 10, 25 ou 50. `modo_prazo: "intervalo"` inicia na criação e vence após
  `prazo_dias` períodos de 24 horas. `modo_prazo: "dia_fixo"` recebe `data_fixa`
  (data local da casa), vence no fim desse dia e abre `prazo_dias` antes.
- `PATCH /tarefas/{id}` edita as regras permitidas para tarefa unitária; o
  cliente envia `prazo_dias` e, no modo de dia fixo, `data_fixa`. `data_fim` é
  calculada pelo backend e não é aceita como entrada. Ocorrências rotativas não
  são editadas individualmente. Datas de instante na resposta usam UTC
  explícito, inclusive para registros legados armazenados sem fuso.
- `POST /rotatividades/` registra a configuração semanal, com dois ou mais
  participantes elegíveis em ordem, `dias_semana` (1 = segunda, 7 = domingo) e
  `intervalo_semanas` de 1 a 4. `GET /rotatividades/{id}/ocorrencias` consulta
  as tarefas geradas. Cada ocorrência possui ID, responsável e histórico
  próprios; uma ocorrência aberta não impede a seguinte. A primeira semana
  agendada é a atual se ainda há um dia programado, ou a próxima se os dias
  escolhidos já passaram.
- O processo `python -m services.rotatividade`, iniciado em `src/backend`,
  verifica a agenda periodicamente, cria as ocorrências devidas e encerra as
  expiradas. A atribuição escolhe, entre os participantes que ainda pertencem
  à casa, quem recebeu menos **pontos possíveis** em ocorrências rotativas da
  casa no mês local da nova ocorrência. A ordem configurada desempata;
  repetições do mesmo responsável são permitidas. Uma versão por casa e a
  unicidade da ocorrência protegem execuções concorrentes ou repetidas. O fuso
  da agenda é guardado na configuração para preservar os dias programados se o
  fuso da casa mudar; o mês do balanceamento segue o fuso atual da casa.
- `PATCH /tarefas/{id}` com apenas `{"estado_atual":"finalizado"}` calcula o
  desconto em Python: `100 / (atraso_maximo + 1)` por dia de atraso, com
  arredondamento final. A operação transacional registra conclusão, um evento
  de crédito e o saldo. A resposta inclui `concluida_em` e
  `resultado_pontuacao` com `pontos_possiveis`, `pontos_ganhos` e
  `saldo_atual`. O frontend mostra os dois valores de pontos da resposta.
- `pertencer.score` é o saldo vitalício materializado. `GET /casas/{id}/placar`
  soma `score_event` por semana (domingo a sábado), mês e ano correntes no
  fuso IANA da casa; também retorna o acumulado dos eventos. O administrador
  usa `GET /casas/{id}/auditoria-score` para ver diferenças entre eventos e
  saldo antes de uma reconciliação. Novas casas usam `America/Sao_Paulo` por
  padrão e o fuso pode ser configurado na API de casas.
- A API de vínculos aceita somente saldo inicial zero e não oferece edição
  livre do saldo. A exclusão de tarefas e vínculos com créditos é bloqueada
  para preservar o histórico do placar.

O frontend grava tarefas e rodízios pela API quando ela está configurada, usa
os campos aceitos pelo `PATCH` na edição e exibe o placar. Sem a API, a tela de
criação continua oferecendo uma prévia local com dados fictícios.

## Arquivos principais

- `src/backend/schemas/` e `src/backend/routers/`: contratos e endpoints de
  tarefas, rodízios, casas e vínculos.
- `src/backend/services/tarefa.py`, `rotatividade.py` e `placar.py`: janelas,
  distribuição mensal, conclusão e agregação do placar.
- `src/frontend/src/app/nova-tarefa.tsx`, `tarefas.tsx` e componentes de
  detalhe/edição: criação, placar, conclusão e edição conectadas à API.
- `docker-compose.yml`: serviço `rotatividade-worker` para a agenda periódica.

## Migrations e histórico

| Arquivo | Papel |
| --- | --- |
| `docs/migrations/14.sql` | Contrato anterior de duração e pontos-base; ainda exigido por bancos que não o aplicaram. |
| `docs/migrations/15.sql` | Remove o trigger de crédito e cria a primeira versão da operação de conclusão. |
| `docs/migrations/16.sql` | Introduz `tipo` e `modo_prazo`; permanece inalterado. |
| `docs/migrations/17.sql` | Acrescenta fuso, esquema do rodízio, unicidade de ocorrências e preservação de eventos; converte datas de eventos legadas assumindo UTC. |
| `docs/migrations/18.sql` | Cria operações transacionais do rodízio e das exclusões protegidas; atualiza a conclusão para devolver a pontuação e o saldo. |
| `docs/migrations/19.sql` | Reconcilia `pertencer.score` com a soma de `score_event`; aplicar somente após revisar a auditoria. |

Confira o histórico efetivamente aplicado no Supabase antes de executar SQL.
No Supabase consultado para esta implementação, a verificação somente de
leitura encontrou colunas da `16.sql`, mas não as colunas da `14.sql` nem a
operação da `15.sql`. Antes de executar SQL, confirme o histórico de aplicação
nesse banco. Se a verificação for confirmada, a sequência pendente começa em
`14.sql` e `15.sql`, continua em `17.sql` e `18.sql`, e só então permite avaliar
a `19.sql`; não reaplique `16.sql`. O arquivo `19.sql`
ajusta somente saldos de vínculos existentes: eventos históricos já apagados
não podem ser reconstruídos a partir do repositório.

## Validação e pendências

Passaram 212 testes unitários do backend, 23 testes do frontend e o typecheck
TypeScript. As migrations `17.sql` a `19.sql` passaram na análise sintática
PostgreSQL. O Ruff dos arquivos alterados do backend e o ESLint dos arquivos
alterados do frontend, com a regra Prettier desabilitada, passaram. O lint global
do frontend ainda encontra erros de formatação e finais de linha existentes no
projeto. A coleta dos
testes de integração passou, mas a execução real de crédito, concorrência,
saldo, eventos e geração de ocorrências depende da aplicação sequencial das
migrations no Supabase exclusivo de testes. As verificações do banco feitas
até aqui foram somente de leitura; nenhuma migration foi aplicada. A validação
em Android e iOS também continua pendente.
