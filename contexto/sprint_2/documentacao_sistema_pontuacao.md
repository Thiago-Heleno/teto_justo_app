# Cálculo de pontuação de tarefas

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

A migration `docs/migrations/14.sql` alinha o trigger de conclusão à mesma
fórmula. O trigger continua sendo o único mecanismo de crédito em `score_event`
e `pertencer.score`. O Python não credita pontos em paralelo, evitando crédito
duplo. A restrição existente por usuário/tarefa preserva a idempotência do evento.

A penalidade reduz os pontos recebidos ao concluir a tarefa; não desconta
periodicamente do saldo. Consultas após a tolerância marcam `nao_feito` sem
crédito. A API bloqueia conclusão repetida, reabertura e alterações de regras
junto da finalização.

A coluna `tarefa.pontuacao` representa somente a base calculada; o valor
creditado está em `score_event.pontuacao`. O cliente não informa `pontuacao`
na criação nem na edição, inclusive quando autenticado como administrador.

## Validação

A suíte unitária aprovada inclui dificuldades, entradas inválidas, períodos
parciais/exatos de 24 horas, N + 1, arredondamento, normalização de fuso e
imutabilidade. A validação do trigger no Supabase está pendente: a migration
foi preparada, mas não foi executada nesta sessão.

Veja [o contrato e as limitações desta entrega](schemas_tarefa.md).
