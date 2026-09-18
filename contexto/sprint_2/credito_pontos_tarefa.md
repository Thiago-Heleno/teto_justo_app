# Crédito de pontos ao finalizar tarefa — Sprint 2

## Objetivo

Creditar pontuação aos responsáveis por uma tarefa automaticamente quando ela é finalizada, aplicando desconto por atraso.

## Alterações

- `docs/migrations/09.sql` cria a função `fn_tarefa_finalizada_credita_pontos` e o trigger `TRG_Tarefa_Finalizada_Credita_Pontos`, disparado `BEFORE UPDATE` em `tarefa` quando `estado_atual` deixa de ser `finalizado` e passa a ser.
- Ao disparar, a função grava `concluida_em = NOW()` na própria linha da tarefa.
- O atraso é calculado em dias inteiros (`FLOOR`) entre `data_fim` e o momento da conclusão, com piso em `0`.
- A taxa de desconto diário depende de `tipo_de_penalidade`: `1` = 10%/dia, `2` = 20%/dia, `3` = 30%/dia, `4` = 40%/dia; sem `tipo_de_penalidade`, a taxa é `0` (pontuação cheia).
- O percentual final é `GREATEST(0, 100 - dias_atraso * taxa_diaria)`, aplicado sobre `NEW.pontuacao` e arredondado (`ROUND`) para gerar `pontos_creditados`.
- Para cada usuário em `atribuida` vinculado à tarefa, a função insere um registro em `score_event` (`fk_usuario_id`, `fk_casa_id`, `fk_tarefa_id`, `pontuacao`) com `ON CONFLICT (fk_usuario_id, fk_tarefa_id) DO NOTHING`, evitando crédito duplicado se a tarefa for finalizada mais de uma vez.
- Somente quando o `INSERT` de fato ocorre (`FOUND`), a função soma `pontos_creditados` em `pertencer.score` do respectivo usuário/casa — mantendo `score_event` e `pertencer.score` consistentes entre si.

## Observações

- O desconto é calculado sobre o tempo corrido até `NOW()`, não até uma eventual data de finalização informada manualmente; por isso `concluida_em` é sempre definido pelo próprio trigger.
- A lógica depende das colunas `dificuldade`/`tipo_de_penalidade`/`pontuacao` e da tabela `score_event` introduzidas em `docs/migrations/07.sql` (ver [pontuacao_tarefa.md](pontuacao_tarefa.md)) e do estado textual `finalizado` introduzido em `docs/migrations/08.sql` (ver [estado_tarefa.md](estado_tarefa.md)).
