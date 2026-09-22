# Crédito de pontos ao finalizar tarefa — Sprint 2

## Objetivo

Creditar pontuação aos responsáveis por uma tarefa automaticamente quando ela é finalizada, aplicando desconto por atraso.

> **Atualizado em 21/09/2026** — a taxa de desconto diário deixou de depender
> de `tipo_de_penalidade` e passou a ser calculada a partir de
> `atraso_maximo` da própria tarefa. Ver
> [edicao_atraso_pontuacao_tarefa.md](edicao_atraso_pontuacao_tarefa.md).

## Alterações

- `docs/migrations/09.sql` cria a função `fn_tarefa_finalizada_credita_pontos` e o trigger `TRG_Tarefa_Finalizada_Credita_Pontos`, disparado `BEFORE UPDATE` em `tarefa` quando `estado_atual` deixa de ser `finalizado` e passa a ser.
- `docs/migrations/10.sql` substitui a função, trocando a taxa diária fixa por `tipo_de_penalidade` por `100% / atraso_maximo` (ver detalhes abaixo).
- Ao disparar, a função grava `concluida_em = NOW()` na própria linha da tarefa.
- O atraso é calculado em dias inteiros (`FLOOR`) entre `data_fim` e o momento da conclusão, com piso em `0`.
- A taxa de desconto diário é `100.0 / atraso_maximo` da tarefa — variável por tarefa, não mais fixa por `tipo_de_penalidade`. No dia em que `dias_atraso` atinge `atraso_maximo`, a perda já chega a 100%.
- O percentual final é `GREATEST(0, 100 - dias_atraso * taxa_diaria)`, aplicado sobre `NEW.pontuacao` e arredondado (`ROUND`) para gerar `pontos_creditados`.
- Para cada usuário em `atribuida` vinculado à tarefa, a função insere um registro em `score_event` (`fk_usuario_id`, `fk_casa_id`, `fk_tarefa_id`, `pontuacao`) com `ON CONFLICT (fk_usuario_id, fk_tarefa_id) DO NOTHING`, evitando crédito duplicado se a tarefa for finalizada mais de uma vez.
- Somente quando o `INSERT` de fato ocorre (`FOUND`), a função soma `pontos_creditados` em `pertencer.score` do respectivo usuário/casa — mantendo `score_event` e `pertencer.score` consistentes entre si.

## Observações

- O desconto é calculado sobre o tempo corrido até `NOW()`, não até uma eventual data de finalização informada manualmente; por isso `concluida_em` é sempre definido pelo próprio trigger.
- A lógica depende das colunas `dificuldade`/`atraso_maximo`/`pontuacao` e da tabela `score_event` introduzidas em `docs/migrations/07.sql` (ver [pontuacao_tarefa.md](pontuacao_tarefa.md)) e do estado textual `finalizado` introduzido em `docs/migrations/08.sql` (ver [estado_tarefa.md](estado_tarefa.md)).
- A coluna `tipo_de_penalidade` foi removida em `docs/migrations/11.sql`, já que não era mais lida por este trigger nem tinha sido exposta pela API Python.
