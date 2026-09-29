# Validação do fluxo completo de pontuação — Sprint 2

## Objetivo

Validar no Supabase de testes o fluxo `Tarefa → Atribuida → ScoreEvent → Pertencer.score`, incluindo placar e auditoria, e confirmar que a suíte e os CRUDs não regrediram.

## Estado do banco

Verificação somente leitura pela API REST do Supabase de testes:

- `score_event` já possui a coluna `tipo` (`docs/migrations/24.sql` aplicada).
- Só `criar_rotatividade` e `registrar_ocorrencia_rotativa` existem como RPC; `registrar_conclusao_tarefa`, `excluir_tarefa_sem_credito` e `excluir_vinculo_sem_credito` foram removidas (`docs/migrations/25.sql` aplicada).

Nenhuma migration foi executada nesta validação: o banco já estava atualizado.

Não há trigger de cálculo no banco. A API REST não expõe `pg_trigger`, então a checagem foi comportamental, com dados temporários removidos ao final: marcar uma tarefa como `finalizado` e inserir um `score_event` direto no Supabase não alterou `pertencer.score` (continuou 0), não preencheu `concluida_em` e não gerou eventos além do inserido. Para listar triggers no SQL Editor: `SELECT tgname, tgrelid::regclass FROM pg_trigger WHERE NOT tgisinternal;`.

## Cobertura do fluxo

Executado por `tests/test_tarefas_integracao.py` contra o Supabase real:

- `test_credito_real_respeita_tolerancia_e_nao_duplica` (no prazo, 1º e 2º dia de atraso e além da tolerância): cria a tarefa com responsável em `atribuida`, conclui, confere o evento em `score_event` (50/33/17/sem evento), `pertencer.score`, `saldo_atual` da resposta, `acumulado` em `GET /casas/{id}/placar`, `divergencias == []` em `GET /casas/{id}/auditoria-score`, bloqueio de conclusão repetida (409) e de exclusão da tarefa creditada (409).
- `test_conclusoes_simultaneas_creditam_uma_unica_vez`: duas conclusões concorrentes resultam em `[200, 409]`, um único evento de 50 pontos e saldo 50.
- `test_conclusao_sem_vinculo_reverte_toda_a_gravacao` e `test_atualizar_estado_diretamente_no_banco_nao_calcula_pontos`: sem vínculo em `pertencer` a conclusão retorna 409 sem escrita; atualizar o estado direto no banco não gera crédito (trigger ausente).

## Resultados

- Testes unitários (comando do CI, sem serviços externos): 212 passaram.
- Testes de integração no Supabase (sessões, tarefas, usuários, casas, vínculos): 23 passaram, incluindo os CRUDs; nenhuma regressão.
- `ruff check .` (backend) e `npm run lint` (frontend) sem erros. O frontend não possui script de testes.
- Na primeira execução completa houve erros transitórios de conexão com o Supabase (`Server disconnected`); a repetição passou. O teste de concorrência falhou uma vez pelo mesmo motivo e passou em duas execuções isoladas seguintes.

## Limitações

- Não há endpoint de extrato por usuário: a leitura dos eventos é feita apenas pela soma no placar e pela auditoria de divergências.
- O placar ordena moradores por nome; não há ordenação por pontos no backend, e os testes de placar usam um único morador.
- O job de integração do CI só roda em `main` ou `workflow_dispatch`; nesta validação foi executado localmente com as credenciais de teste.
