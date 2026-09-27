# Alinhamento de tarefas e pontuação — Sprint 2

## Objetivo

Unificar o contrato de criação, edição e conclusão de tarefas com o placar.
A integração ativa do rodízio foi retirada do backend e da gravação no frontend;
a prévia de tarefa rotativa que já existia na interface permanece. As migrations
`17.sql` a `19.sql` permanecem intactas e não foram aplicadas nesta retirada.
As descrições de entregas anteriores em outros documentos da sprint são
históricas.

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
campos aceitos pelo `PATCH` na edição e exibe o placar. A opção rotativa mantém
somente a prévia local, sem gravar configuração ou gerar ocorrências. Sem a API,
a tela de criação oferece uma prévia local com dados fictícios.

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
| `docs/migrations/16.sql` | Introduz `tipo` e `modo_prazo`; permanece inalterado. |
| `docs/migrations/17.sql` | Acrescenta fuso, esquema do rodízio, unicidade de ocorrências e preservação de eventos; converte datas de eventos legadas assumindo UTC. |
| `docs/migrations/18.sql` | Cria operações transacionais do rodízio e das exclusões protegidas; atualiza a conclusão para devolver a pontuação e o saldo. |
| `docs/migrations/19.sql` | Reconcilia `pertencer.score` com a soma de `score_event`; aplicar somente após revisar a auditoria. |
| `docs/migrations/20.sql` | Remove o trigger e a função legados caso `14.sql` seja aplicada depois de `15.sql`; exige as estruturas das duas migrations. |

O esquema e as funções de rodízio continuam em `17.sql` e `18.sql`, mas não
têm rota, serviço periódico nem gravação no frontend. Sua eventual aplicação
deixará esses objetos sem consumidor ativo. Nenhuma migration foi editada ou
executada nesta retirada.

Confira o histórico efetivamente aplicado no Supabase antes de executar SQL.
No Supabase de desenvolvimento consultado nesta entrega, a API expõe as colunas
da `16.sql` e a função de conclusão com a assinatura da `15.sql`, mas o banco
rejeita `tarefa.prazo_dias` e `casa.timezone` como colunas inexistentes. O
catálogo SQL ainda precisa confirmar constraints, trigger e histórico antes de
qualquer aplicação. Se confirmar esse estado, a ordem é `14.sql`, `20.sql`,
`17.sql`, `18.sql`; não reaplicar `15.sql` ou `16.sql`. `19.sql` permanece
pendente da auditoria: eventos históricos já apagados não podem ser
reconstruídos a partir do repositório.

## Validação e pendências

O workflow unitário passou a descobrir todos os testes fora de
`*_integracao.py`, incluindo a conclusão. Foram acrescentados testes de tipo e
modo de prazo para validação HTTP e persistência real de `intervalo` e
`dia_fixo`. Passaram 206 testes unitários, Ruff e `git diff --check`; 23 testes
de integração foram coletados, e 4 testes de usuários e sessões passaram no
Supabase de desenvolvimento. Os testes de tarefas, casas e vínculos aguardam a
aplicação das migrations pelo SQL Editor.
Nenhuma migration foi aplicada nesta entrega; `17.sql` a `19.sql` não foram
alteradas. A validação em Android e iOS permanece pendente.
