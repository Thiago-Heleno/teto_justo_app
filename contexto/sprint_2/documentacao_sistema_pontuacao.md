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
A gravação em si também é feita pelo backend, sem função no banco
(`ServicoTarefa._creditar_e_finalizar`/`_creditar_pertencer`/
`_finalizar_estado_tarefa`; ver [concorrencia_retry.md](concorrencia_retry.md)
para o desenho de concorrência). Como o cliente do Supabase não sustenta uma
transação entre múltiplas chamadas, não existe um único `COMMIT` que grava
tudo junto: o `INSERT` em `score_event` decide a corrida entre conclusões
concorrentes (a `UNIQUE`/índice parcial garante crédito único), o crédito em
`pertencer.score` usa um `UPDATE` condicional com novas tentativas em caso de
conflito, e o `UPDATE` que marca a tarefa como `finalizado` é a última
escrita — se ela não achar a linha esperada porque outra requisição
concorrente já mudou o estado, a conclusão retorna `409` em vez de reverter
as escritas já feitas.

A gravação confere se as regras e o responsável ainda são os usados no
cálculo e rejeita uma conclusão já registrada. O incremento do saldo é
protegido contra perder créditos de tarefas concluídas simultaneamente.

Escrever em `pertencer`/`score_event` continua restrito a quem tem a chave
`service_role` (usada pelo backend); os papéis públicos `anon` e
`authenticated` não podem fornecer pontos — antes isso vinha do `GRANT` da
função no banco, agora vem de um `REVOKE` direto nessas tabelas
(`docs/migrations/18.sql`). O responsável precisa ter vínculo em `pertencer`;
se ele for apenas proprietário da casa sem esse vínculo, a conclusão retorna
409 antes de qualquer escrita. Tarefas legadas com múltiplos responsáveis
também exigem regularização antes de serem concluídas.

A função SQL `registrar_conclusao_tarefa` (que fazia essa persistência antes)
continua existindo no banco, sem uso — mantida como rede de segurança até a
migração ser validada em produção por mais tempo.

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
qualquer reconciliação. A migration `docs/migrations/23.sql` ajusta os saldos
existentes à soma dos eventos somente após essa revisão. Eventos históricos
apagados não podem ser reconstruídos a partir do repositório.

## Validação

A suíte unitária aprovada inclui dificuldades, entradas inválidas, períodos
parciais/exatos de 24 horas, N + 1, arredondamento, normalização de fuso e
imutabilidade, o valor enviado à persistência e o tratamento de
conflitos/falhas (incluindo o CAS de `pertencer.score` e a recuperação de
violação de unicidade em `score_event`). A suíte de integração contra o
Supabase real (`test_tarefas_integracao.py`) cobre ausência do trigger,
reversão por falta de vínculo e conclusões concorrentes — foi essa última
que revelou um caso de corrida que os testes unitários com mock não
conseguiam pegar (ver "Lição aprendida" em
[concorrencia_retry.md](concorrencia_retry.md)).

Veja [o contrato e as limitações desta entrega](schemas_tarefa.md).
