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
| `docs/migrations/14.sql` | Contrato anterior de duração e pontos-base; ainda exigido por bancos que não o aplicaram. |
| `docs/migrations/15.sql` | Remove o trigger de crédito e cria a primeira versão da operação de conclusão. |
| `docs/migrations/16.sql` | Cria a primeira função SQL de conclusão da tarefa. |
| `docs/migrations/17.sql` | Acrescenta `tipo` e `modo_prazo` à tarefa. |
| `docs/migrations/18.sql` | Cria as tabelas do rodízio e as colunas de vínculo/unicidade das ocorrências. |
| `docs/migrations/19.sql` | Cria a função SQL de criação de rodízio; não é usada pela implementação atual. |
| `docs/migrations/21.sql` | Cria a função SQL de registro de ocorrência; não é usada pela implementação atual. |

O esquema de rodízio em `18.sql` é usado pela integração. As funções SQL de
`19.sql` e `21.sql` não são chamadas: criação, seleção do responsável e gravação
da ocorrência são feitas no backend. Nenhuma migration foi alterada ou
executada. O banco verificado anteriormente não tinha o esquema necessário para
o rodízio; portanto, a funcionalidade só poderá operar em um ambiente onde as
tabelas e colunas descritas nas migrations requeridas já estejam aplicadas.

Confira o histórico efetivamente aplicado no Supabase antes de habilitar o
rodízio. A verificação somente de leitura registrada anteriormente encontrou
colunas da `16.sql`, mas não as colunas da `14.sql` nem a operação da `15.sql`.
Não aplique SQL como parte desta mudança. A implementação precisa que as tabelas
e colunas de `18.sql` já existam; ela não precisa das funções SQL de `19.sql` ou
`21.sql`.

## Validação e pendências

Na implementação atual, passaram 267 testes unitários do backend, 24 testes
do frontend, Ruff dos arquivos Python alterados e `git diff --check`. O
typecheck do frontend, lint completo e validação com Supabase real não foram
executados. Nenhuma migration foi aplicada. A gravação de configuração e a
gravação da ocorrência/atribuição são escritas separadas; o job precisa rodar
em uma única instância ativa até haver uma estratégia de concorrência
distribuída. A validação em Android e iOS também continua pendente.
