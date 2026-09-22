# Sistema de Pontuação de Tarefas

## 1. Objetivo

Este documento define as regras de pontuação e penalidade por atraso aplicadas ao usuário atribuído a uma tarefa.

As regras devem ser aplicadas de forma determinística no backend, garantindo que a mesma tarefa sempre produza o mesmo resultado para os mesmos dados de entrada.

## 2. Níveis de dificuldade

Cada tarefa deve possuir exatamente um nível de dificuldade, definido no momento de sua criação.

| Nível | Pontuação-base | Descrição sugerida |
| --- | ---: | --- |
| Fácil | 10 pontos | Tarefa simples, curta ou de baixa complexidade. |
| Média | 20 pontos | Tarefa que exige esforço moderado ou mais tempo. |
| Difícil | 30 pontos | Tarefa complexa, longa ou de maior responsabilidade. |

A pontuação-base pertence à tarefa e, depois das penalidades aplicáveis, é concedida ao seu único usuário atribuído.

## 3. Datas e contagem de atraso

Cada tarefa deve possuir:

- `data_limite`: data até a qual a tarefa pode ser concluída sem penalidade;
- `data_conclusao`: data em que a tarefa foi efetivamente concluída;
- `dias_atraso`: quantidade de dias corridos de atraso.

O cálculo deve considerar somente a parte da data, desconsiderando hora, minuto, segundo e fuso horário depois de as datas serem normalizadas para o fuso horário oficial da aplicação.

```text
dias_atraso = max(0, data_conclusao - data_limite)
```

Regras:

- conclusão antes ou na `data_limite`: `dias_atraso = 0`;
- conclusão no dia seguinte: `dias_atraso = 1`;
- sábados, domingos e feriados são contados, pois o cálculo utiliza dias corridos;
- tarefas ainda não concluídas podem exibir uma projeção da penalidade com base na data atual, mas os pontos somente devem ser consolidados na conclusão;
- alterações posteriores de datas devem exigir o recálculo da pontuação.

## 4. Tipos de penalidade

A tarefa deve indicar um tipo de penalidade:

- `FIXA`;
- `VARIAVEL`.

Uma tarefa não pode utilizar os dois tipos simultaneamente. Quando não houver atraso, nenhum tipo de penalidade reduz a pontuação.

## 5. Penalidade fixa

Na penalidade fixa, perde-se 20% da pontuação-base por dia de atraso, até o limite de 100%.

```text
percentual_perdido = min(100%, dias_atraso × 20%)
percentual_mantido = max(0%, 100% - percentual_perdido)
pontuacao_calculada = pontuacao_base × percentual_mantido
```

| Dias de atraso | Perda | Pontuação mantida |
| ---: | ---: | ---: |
| 0 | 0% | 100% |
| 1 | 20% | 80% |
| 2 | 40% | 60% |
| 3 | 60% | 40% |
| 4 | 80% | 20% |
| 5 ou mais | 100% | 0% |

Exemplo para uma tarefa de 30 pontos concluída com 3 dias de atraso:

```text
pontuacao_calculada = 30 × (1 - 0,60) = 12 pontos
```

## 6. Penalidade variável

Na penalidade variável, a configuração `dias_para_zerar` determina em quantos dias de atraso a tarefa perderá 100% dos pontos. A perda é distribuída igualmente entre esses dias.

```text
percentual_por_dia = 100% / dias_para_zerar
percentual_perdido = min(100%, dias_atraso × percentual_por_dia)
percentual_mantido = max(0%, 100% - percentual_perdido)
pontuacao_calculada = pontuacao_base × percentual_mantido
```

### Exemplo: prazo variável de 2 dias

Quando `dias_para_zerar = 2`, a tarefa perde 50% por dia:

| Dias de atraso | Perda | Pontuação mantida |
| ---: | ---: | ---: |
| 0 | 0% | 100% |
| 1 | 50% | 50% |
| 2 ou mais | 100% | 0% |

Para uma tarefa de 20 pontos concluída com 1 dia de atraso:

```text
pontuacao_calculada = 20 × (1 - 0,50) = 10 pontos
```

`dias_para_zerar` deve ser um número inteiro maior que zero. Valores nulos, iguais a zero ou negativos devem ser rejeitados na validação quando o tipo escolhido for `VARIAVEL`.

## 7. Limite mínimo e máximo

A pontuação final da tarefa deve permanecer no intervalo entre zero e a pontuação-base:

```text
pontuacao_limitada = min(pontuacao_base, max(0, pontuacao_calculada))
```

Consequentemente:

- a pontuação nunca pode ser negativa;
- atrasos adicionais após a pontuação chegar a zero não geram dívida;
- a tarefa nunca concede mais pontos que sua pontuação-base;
- a penalidade de uma tarefa não reduz o saldo que o usuário já possuía.

## 8. Usuário atribuído

Cada tarefa deve possuir exatamente um `usuario_atribuido`. A pontuação final da tarefa deve ser concedida integralmente a esse usuário, sem rateio.

Regras:

- uma tarefa não pode ser criada ou concluída sem `usuario_atribuido`;
- uma tarefa não pode possuir mais de um usuário atribuído;
- se o usuário atribuído for alterado antes da conclusão, os pontos serão concedidos ao novo responsável;
- depois da conclusão e da concessão dos pontos, a troca de responsável deve exigir o estorno do lançamento anterior e a criação de um novo lançamento para o usuário correto;
- a conclusão de uma tarefa deve gerar apenas um lançamento de pontuação, evitando concessões duplicadas.

## 9. Arredondamento

Os percentuais devem ser calculados com precisão decimal, sem arredondamentos intermediários. O arredondamento deve ocorrer uma única vez, depois da aplicação da penalidade.

Regra adotada:

```text
pontuacao_da_tarefa = round_half_up(pontuacao_limitada)
```

No método `round_half_up`, valores com parte decimal igual ou superior a `0,5` são arredondados para o inteiro seguinte. Exemplos:

| Valor calculado | Valor inteiro |
| ---: | ---: |
| 7,49 | 7 |
| 7,50 | 8 |
| 12,00 | 12 |

Não deve ser utilizado o arredondamento bancário (`round half to even`), pois ele pode produzir resultados diferentes nos casos terminados em `0,5`.

## 10. Ordem completa do cálculo

O sistema deve executar as operações nesta ordem:

1. validar o nível de dificuldade e obter a pontuação-base;
2. normalizar `data_limite` e `data_conclusao`;
3. calcular `dias_atraso`;
4. calcular o percentual perdido conforme o tipo de penalidade;
5. aplicar os limites mínimo zero e máximo igual à pontuação-base;
6. arredondar a pontuação total uma única vez;
7. conceder a pontuação final ao único `usuario_atribuido`;
8. registrar o resultado e os parâmetros usados no cálculo.

## 11. Pseudocódigo de referência

```text
calcular_pontuacao(tarefa):
    base = pontos_por_dificuldade(tarefa.dificuldade)
    usuario = tarefa.usuario_atribuido

    se usuario estiver vazio:
        retornar erro "Tarefa sem usuário atribuído"

    atraso = max(0, diferenca_em_dias(
        tarefa.data_conclusao,
        tarefa.data_limite
    ))

    se tarefa.tipo_penalidade == FIXA:
        perda = min(1, atraso * 0.20)
    senao se tarefa.tipo_penalidade == VARIAVEL:
        validar tarefa.dias_para_zerar > 0
        perda = min(1, atraso / tarefa.dias_para_zerar)
    senao:
        retornar erro "Tipo de penalidade inválido"

    calculada = base * (1 - perda)
    limitada = min(base, max(0, calculada))
    total = round_half_up(limitada)

    retornar {
        pontuacao_base: base,
        dias_atraso: atraso,
        percentual_perdido: perda,
        pontuacao_final: total,
        usuario_atribuido: usuario
    }
```

## 12. Casos de teste mínimos

| Cenário | Resultado esperado |
| --- | --- |
| Tarefa de 10 pontos concluída no prazo | 10 pontos |
| Tarefa de 20 pontos, penalidade fixa e 1 dia de atraso | 16 pontos |
| Tarefa de 30 pontos, penalidade fixa e 4 dias de atraso | 6 pontos |
| Tarefa de 30 pontos, penalidade fixa e 5 dias de atraso | 0 pontos |
| Tarefa de 20 pontos, variável em 2 dias e 1 dia de atraso | 10 pontos |
| Tarefa de 20 pontos, variável em 2 dias e 2 dias de atraso | 0 pontos |
| Tarefa sem usuário atribuído | Erro ou pendência, sem concessão de pontos |
| Tarefa com mais de um usuário atribuído | Erro de validação |
| Tarefa válida concluída | Um único lançamento integral para o usuário atribuído |
| Tarefa cuja penalidade excederia 100% | 0 pontos, nunca valor negativo |

## 13. Dados recomendados para auditoria

Para permitir conferência e evitar divergências futuras, cada concessão de pontos deve registrar:

- identificador da tarefa;
- dificuldade e pontuação-base;
- tipo e parâmetros da penalidade;
- data-limite e data de conclusão;
- dias de atraso;
- percentual perdido;
- pontuação calculada antes do arredondamento;
- pontuação final arredondada;
- identificador do único usuário atribuído e pontuação recebida;
- data e versão da regra usada no cálculo.

## 14. Decisões adotadas nesta especificação

Esta documentação adota as seguintes interpretações das regras propostas:

- o primeiro dia após a data-limite já corresponde a um dia de atraso;
- a penalidade fixa começa em 20% no primeiro dia de atraso e aumenta 20 pontos percentuais por dia;
- a penalidade variável representa a quantidade de dias de atraso necessária para zerar a tarefa;
- a contagem utiliza dias corridos;
- cada tarefa possui exatamente um usuário atribuído;
- a pontuação final é concedida integralmente a esse usuário, sem rateio.

Caso alguma dessas decisões seja alterada, a versão da regra também deve ser atualizada para preservar a rastreabilidade das pontuações já registradas.
