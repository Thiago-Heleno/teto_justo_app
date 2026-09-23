# Base de cálculo do score

## Objetivo e estado da entrega

O `ServicoScore` centraliza a regra matemática de pontuação de tarefas em um componente puro e determinístico. O resultado depende somente dos argumentos recebidos: o serviço não acessa banco de dados, FastAPI ou o horário atual do sistema.

Nesta etapa, o serviço é apenas a base de cálculo. Ele ainda não está ligado à conclusão de tarefas, não persiste eventos em `score_event`, não altera o saldo de `pertencer` e não substitui o trigger SQL existente.

## Interface do cálculo

```python
calcular_score(
    peso: int,
    prazo_dias: int,
    data_fim: datetime,
    concluida_em: datetime,
    usuarios_atribuidos: Sequence[UUID],
) -> ResultadoScore
```

O resultado é imutável e registra os dados necessários para compreender o cálculo:

- responsável;
- pontos-base;
- prazo em dias;
- dias de atraso;
- percentual descontado por dia;
- desconto aplicado;
- pontos finais.

## Pontos-base

O peso da tarefa determina os pontos disponíveis antes da penalidade:

| Peso | Nível | Pontos-base |
| ---: | --- | ---: |
| 1 | Básico | 10 |
| 2 | Intermediário | 25 |
| 3 | Difícil | 50 |

Pesos diferentes de `1`, `2` e `3` são inválidos. No contrato puro do `ServicoScore`, os pontos não são recebidos como valor livre: eles são obtidos por esse mapeamento. O contrato HTTP atual continua inalterado nesta etapa.

## Prazo e atraso

`prazo_dias` representa a duração usada para distribuir 100% dos pontos. Ele deve ser um número inteiro maior que zero. O limite de produto de 1 a 5 dias continua sendo responsabilidade da interface; o cálculo puro aceita qualquer inteiro positivo.

As datas com fuso horário são comparadas em UTC. Datas sem fuso são interpretadas como UTC. `concluida_em` é informado explicitamente para que o resultado não dependa de `datetime.now()`.

Uma conclusão anterior ou igual a `data_fim` não possui atraso. Qualquer atraso positivo já inicia a primeira faixa de 24 horas:

```text
diferença <= 0                         -> 0 dias de atraso
0 < diferença < 24 horas               -> 1 dia de atraso
24 horas <= diferença < 48 horas       -> 2 dias de atraso
cada nova faixa de 24 horas iniciada   -> mais 1 dia de atraso
```

Assim, a contagem usa a duração efetiva entre os instantes, e não apenas a diferença entre datas do calendário.

## Fórmula proporcional

O prazo distribui igualmente 100% da pontuação:

```text
percentual_por_dia = 100 / prazo_dias
desconto_por_dia = pontos_base / prazo_dias
desconto = min(pontos_base, dias_atraso × desconto_por_dia)
pontos_brutos = max(0, pontos_base - desconto)
pontos_finais = ROUND_HALF_UP(pontos_brutos)
```

Os cálculos usam `Decimal`, sem arredondamentos intermediários. O arredondamento acontece uma única vez no resultado final, com `ROUND_HALF_UP`; portanto, valores terminados em `0,5` avançam para o próximo inteiro. A pontuação nunca ultrapassa os pontos-base e nunca fica negativa.

Exemplos:

| Peso | Pontos-base | Prazo | Atraso | Cálculo antes do arredondamento | Pontos finais |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 10 | 2 dias | 0 | 10 | 10 |
| 1 | 10 | 2 dias | 1 faixa | 5 | 5 |
| 1 | 10 | 2 dias | 2 faixas | 0 | 0 |
| 2 | 25 | 2 dias | 1 faixa | 12,5 | 13 |
| 3 | 50 | 5 dias | 2 faixas | 30 | 30 |

Não existem mais estratégias separadas de penalidade fixa e variável nesta regra. O desconto é sempre proporcional a `prazo_dias`.

## Responsável e rateio

O cálculo exige exatamente um usuário atribuído à tarefa. Uma coleção vazia, com identificadores duplicados ou com mais de um usuário é inválida e gera `ValueError`.

Toda a pontuação calculada pertence ao único responsável. Não há rateio nesta implementação.

## Ordem do cálculo

1. Validar o peso e obter os pontos-base.
2. Validar `prazo_dias`.
3. Validar que existe exatamente um responsável.
4. Normalizar os dois instantes para UTC.
5. Calcular as faixas de atraso iniciadas.
6. Aplicar o desconto proporcional e o limite mínimo de zero.
7. Arredondar uma única vez com `ROUND_HALF_UP`.
8. Retornar o `ResultadoScore` imutável.

## Relação com o trigger SQL atual

O trigger de `docs/migrations/10.sql` permanece inalterado e usa uma regra diferente da base Python:

- recebe os pontos de `tarefa.pontuacao`, em vez de derivá-los do peso `1`, `2` ou `3`;
- divide 100% por `atraso_maximo`, em vez de usar `prazo_dias`;
- calcula o atraso com `FLOOR`, de modo que um atraso positivo inferior a 24 horas ainda resulte em zero dias;
- percorre todos os registros de `atribuida` e concede a pontuação integral a cada um;
- persiste em `score_event` e atualiza `pertencer.score`.

Portanto, a fórmula proporcional central já existia parcialmente no SQL como `100 / atraso_maximo`, mas a nova fórmula central do `ServicoScore` é uma implementação distinta. As migrations e o trigger não foram modificados nesta entrega, e os dois mecanismos não devem ser executados simultaneamente quando a integração futura for feita.

## Validações executadas

- `33` testes específicos do `ServicoScore` aprovados, cobrindo o mapeamento
  de pesos, entradas inválidas, prazo positivo, normalização de datas, limites
  das faixas de 24 horas, limite mínimo de zero, arredondamento, responsável
  único, repetibilidade e imutabilidade do resultado.
- Suíte unitária configurada no workflow: `126` testes aprovados.
- Coleta completa: `139` testes encontrados.
- Ruff, Bandit e compilação dos módulos Python concluídos sem erro.
- Testes de integração não foram executados, pois esta etapa não integra o
  cálculo ao Supabase nem modifica o fluxo persistido.

## Pendências

Antes de tornar o novo cálculo autoritativo, ainda será necessário:

- integrá-lo ao fluxo de conclusão da tarefa;
- alinhar o modelo persistido com `prazo_dias`, pesos de 1 a 3 e um único responsável;
- substituir o trigger legado, evitando crédito duplicado;
- impedir alterações públicas diretas de `pertencer.score`;
- definir e registrar os dados necessários à auditoria de cada crédito.
