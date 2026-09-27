# Cálculo de pontuação de tarefas

Este documento descreve a fórmula vigente. O contrato de conclusão, o placar e
as migrations posteriores estão resumidos em
[alinhamento_tarefas_pontuacao.md](alinhamento_tarefas_pontuacao.md).

O `ServicoScore` é um cálculo puro: recebe dificuldade, tolerância, vencimento,
conclusão e o único responsável, sem acessar banco ou relógio do sistema.

```python
calcular_score(
    peso: int,
    atraso_maximo: int,
    data_fim: datetime,
    concluida_em: datetime,
    usuarios_atribuidos: Sequence[UUID],
) -> ResultadoScore
```

## Regra vigente

| Dificuldade (`peso`) | Pontos-base |
| ---: | ---: |
| 1 | 10 |
| 2 | 25 |
| 3 | 50 |

O prazo normal (`prazo_dias`) determina quando a tarefa vence. A tolerância
(`atraso_maximo`) determina o desconto após o vencimento. São valores separados.

Para tolerância N, cada dia de atraso desconta `100 / (N + 1)` por cento dos
pontos-base. O primeiro desconto ocorre após o vencimento; cada período de
até 24 horas de atraso conta como um dia. No limite exato de 24 horas, conta
um dia; no limite de 48 horas, dois.

```text
divisor = atraso_maximo + 1
dias_atraso = CEIL(max(0, concluida_em - data_fim) / 24 horas)
pontos_brutos = pontos_base × max(0, divisor - dias_atraso) / divisor
pontos_finais = ROUND_HALF_UP(pontos_brutos)
```

Não há arredondamento intermediário. A pontuação permanece entre zero e a
base. Com dificuldade 3 e tolerância de 2 dias, os créditos são 50 no prazo,
33 no primeiro dia de atraso, 17 no segundo e zero ao ultrapassar a tolerância.
A taxa é cerca de 33,33% por dia; o primeiro dia preserva 66,67% dos pontos.

O resultado imutável inclui responsável, dificuldade, pontos-base,
`atraso_maximo`, dias de atraso, taxa/descontos e pontos finais. O cálculo exige
exatamente um responsável. Datas com fuso são normalizadas para UTC; datas
legadas sem fuso são tratadas como UTC.

## Crédito persistido

O `ServicoTarefa` chama `ServicoScore.calcular_score` na conclusão e define
`concluida_em` no backend. Dificuldade, atraso, taxa e arredondamento são
calculados exclusivamente em Python.

A migration `docs/migrations/15.sql` remove o trigger e sua função de cálculo.
O backend envia o resultado para `registrar_conclusao_tarefa`, uma operação
explícita de persistência que grava conclusão, evento e incremento do saldo
na mesma transação. Essa operação não contém a fórmula de pontuação.

A gravação bloqueia a tarefa, confere se as regras e o responsável ainda são
os usados no cálculo e rejeita uma conclusão já registrada. Qualquer falha
reverte todas as escritas. O incremento do saldo é atômico para não perder
créditos de tarefas concluídas simultaneamente.

A operação aceita chamadas apenas com o papel `service_role`, usado pelo
backend; os papéis públicos `anon` e `authenticated` não podem fornecer pontos.
O responsável precisa ter vínculo em `pertencer`; se ele for apenas proprietário
da casa sem esse vínculo, a conclusão retorna 409 sem gravação parcial.
Tarefas legadas com múltiplos responsáveis também exigem regularização antes
de serem concluídas.

A penalidade reduz os pontos recebidos ao concluir a tarefa; não desconta
periodicamente do saldo. Consultas após a tolerância marcam `nao_feito` sem
crédito. A API bloqueia conclusão repetida, reabertura e alterações de regras
junto da finalização.

A coluna `tarefa.pontuacao` representa somente a base calculada; o valor
creditado está em `score_event.pontuacao`. O cliente não informa `pontuacao`
na criação nem na edição, inclusive quando autenticado como administrador.

A resposta da conclusão inclui `concluida_em` e `resultado_pontuacao`, com
`pontos_possiveis`, `pontos_ganhos` e `saldo_atual`. O frontend usa esses
valores da mesma operação transacional. `pertencer.score` permanece o saldo
vitalício materializado, enquanto o placar semanal, mensal e anual soma
`score_event` no fuso da casa; a semana vai de domingo a sábado.

O administrador pode consultar `GET /casas/{id}/auditoria-score` antes de
qualquer reconciliação. A migration `docs/migrations/19.sql` ajusta os saldos
existentes à soma dos eventos somente após essa revisão. Eventos históricos
apagados não podem ser reconstruídos a partir do repositório.

## Validação

A suíte unitária aprovada inclui dificuldades, entradas inválidas, períodos
parciais/exatos de 24 horas, N + 1, arredondamento, normalização de fuso e
imutabilidade, valor enviado à persistência e tratamento de conflitos/falhas.
A validação real da transação no Supabase ainda depende da aplicação das
migrations no ambiente de testes. Os testes de integração previstos incluem
ausência do trigger, reversão por falta de vínculo e conclusões concorrentes.

Veja [o contrato e as limitações desta entrega](schemas_tarefa.md).
