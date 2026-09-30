# Consultas e validação de pontuação — Sprint 2

## Objetivo

Disponibilizar saldo por usuário e casa, extrato de `score_event` e ranking dos moradores com filtro por período. Preservar o placar e a auditoria existentes, com consultas e agregação no backend, sem novas funções, triggers ou migrations no banco.

## Endpoints de consulta

Todas as rotas exigem sessão Bearer e acesso à casa como proprietário ou morador. O `id_casa` do caminho corresponde a `fk_casa_id`; moradores podem consultar os pontos dos demais moradores da mesma casa.

| Método e rota | Parâmetros de consulta | Resultado |
| --- | --- | --- |
| `GET /casas/{id_casa}/saldo` | `fk_usuario_id` obrigatório | `fk_casa_id`, `fk_usuario_id` e `saldo_atual`, lido de `pertencer.score`. |
| `GET /casas/{id_casa}/extrato` | `fk_usuario_id`, `data_inicio`, `data_fim`, `inicio`, `limite`, todos opcionais | Eventos da casa, ou de um morador, com total de registros após os filtros e metadados de período e paginação. |
| `GET /casas/{id_casa}/ranking` | `data_inicio` e `data_fim`, opcionais | Moradores com `usuario_id`, `nome`, `pontos` e `posicao`, além da casa, fuso e período consultado. |

### Período e ordenação

- As datas usam `YYYY-MM-DD`, à meia-noite no fuso da casa. `data_inicio` é inclusiva e `data_fim` é exclusiva. Para setembro de 2026: `?data_inicio=2026-09-01&data_fim=2026-10-01`.
- Sem datas, extrato e ranking consideram todo o histórico. Também é possível fornecer apenas um limite. O saldo é sempre o valor atual materializado, sem filtro temporal.
- O extrato usa `inicio=0` e `limite=100` por padrão; aceita início não negativo e limite entre 1 e 100. Ordena por `criado_em` decrescente, com desempate por `id` decrescente. Cada evento contém `id`, as três chaves estrangeiras, `pontuacao`, `tipo` e `criado_em`.
- O ranking soma a pontuação assinada dos eventos, incluindo estornos (`reversal`), apenas para moradores vinculados à casa. Moradores sem eventos aparecem com zero. Pontuações iguais compartilham posição (`1, 2, 2, 4`), com ordem estável por nome e UUID.
- Os filtros de casa, usuário e período são enviados nas consultas de leitura. A soma e a classificação são feitas em Python; eventos e vínculos são lidos em páginas para não truncar o ranking no limite de uma resposta do Supabase.
- Ausência de sessão retorna `401`; usuário sem acesso, `403`; casa ou vínculo solicitado inexistente, `404`; datas, UUIDs, período invertido/vazio ou paginação inválidos, `422`.
- Extrato sem eventos e casa sem moradores retornam listas vazias. Nenhuma dessas consultas altera o saldo ou os eventos.

### Arquivos alterados

- `src/backend/routers/casa.py`: três rotas protegidas, mantendo os contratos de placar e auditoria.
- `src/backend/schemas/score.py`: filtros validados e respostas documentadas no OpenAPI.
- `src/backend/services/placar.py`: consultas, limites de período no fuso da casa, paginação e ranking; reaproveita a consulta de vínculo do `ServicoPertencer`.
- `src/backend/tests/test_servico_placar_unitario.py` e `src/backend/tests/test_consultas_score_router_unitario.py`: testes com banco falso e chamadas HTTP locais, sem integração externa.

### Validação desta implementação

Executados a partir de `src/backend`, com credenciais fictícias e dependências de teste em diretório temporário:

- `python -m pytest -q tests/test_servico_placar_unitario.py tests/test_consultas_score_router_unitario.py -p no:cacheprovider`: **48 passaram**.
- `python -m pytest -q tests --ignore-glob='*_integracao.py' -p no:cacheprovider`: **253 passaram**.
- `ruff check --no-cache .` e `git diff --check`: sem erros.

Cobertura: isolamento de casa/usuário, autenticação e autorização, validação dos filtros, saldo materializado, virada de mês, mudança de horário de verão, estornos, empates, múltiplas páginas, moradores sem eventos e ausência de escritas. A suíte emitiu dois avisos de depreciação das dependências do cliente de testes.

Não foi executada integração com Supabase real nesta implementação. A paginação por deslocamento não oferece um retrato transacional entre requisições: novos eventos podem deslocar páginas durante a leitura. O ranking segue o histórico, enquanto o saldo consulta `pertencer.score`; divergências continuam verificáveis pela auditoria existente.

## Validação anterior no Supabase de testes

Os registros abaixo descrevem a validação anterior do fluxo `Tarefa → Atribuida → ScoreEvent → Pertencer.score`; não representam uma nova execução nesta entrega.

### Estado do banco

Verificação somente leitura pela API REST do Supabase de testes:

- `score_event` já possui a coluna `tipo` (`docs/migrations/24.sql` aplicada).
- Só `criar_rotatividade` e `registrar_ocorrencia_rotativa` existem como RPC; `registrar_conclusao_tarefa`, `excluir_tarefa_sem_credito` e `excluir_vinculo_sem_credito` foram removidas (`docs/migrations/25.sql` aplicada).

Nenhuma migration foi executada nesta validação: o banco já estava atualizado.

Não há trigger de cálculo no banco. A API REST não expõe `pg_trigger`, então a checagem foi comportamental, com dados temporários removidos ao final: marcar uma tarefa como `finalizado` e inserir um `score_event` direto no Supabase não alterou `pertencer.score` (continuou 0), não preencheu `concluida_em` e não gerou eventos além do inserido. Para listar triggers no SQL Editor: `SELECT tgname, tgrelid::regclass FROM pg_trigger WHERE NOT tgisinternal;`.

### Cobertura do fluxo

Executado por `tests/test_tarefas_integracao.py` contra o Supabase real:

- `test_credito_real_respeita_tolerancia_e_nao_duplica` (no prazo, 1º e 2º dia de atraso e além da tolerância): cria a tarefa com responsável em `atribuida`, conclui, confere o evento em `score_event` (50/33/17/sem evento), `pertencer.score`, `saldo_atual` da resposta, `acumulado` em `GET /casas/{id}/placar`, `divergencias == []` em `GET /casas/{id}/auditoria-score`, bloqueio de conclusão repetida (409) e de exclusão da tarefa creditada (409).
- `test_conclusoes_simultaneas_creditam_uma_unica_vez`: duas conclusões concorrentes resultam em `[200, 409]`, um único evento de 50 pontos e saldo 50.
- `test_conclusao_sem_vinculo_reverte_toda_a_gravacao` e `test_atualizar_estado_diretamente_no_banco_nao_calcula_pontos`: sem vínculo em `pertencer` a conclusão retorna 409 sem escrita; atualizar o estado direto no banco não gera crédito (trigger ausente).

### Resultados anteriores

- Testes unitários (comando do CI, sem serviços externos): 212 passaram.
- Testes de integração no Supabase (sessões, tarefas, usuários, casas, vínculos): 23 passaram, incluindo os CRUDs; nenhuma regressão.
- `ruff check .` (backend) e `npm run lint` (frontend) sem erros. O frontend não possui script de testes.
- Na primeira execução completa houve erros transitórios de conexão com o Supabase (`Server disconnected`); a repetição passou. O teste de concorrência falhou uma vez pelo mesmo motivo e passou em duas execuções isoladas seguintes.

### Limitações da validação anterior

- O placar continua ordenando por nome; a ordenação por pontos está na nova rota `/ranking`. As novas consultas de ranking e extrato foram verificadas apenas com banco falso nesta entrega.
- O job de integração do CI só roda em `main` ou `workflow_dispatch`; nesta validação foi executado localmente com as credenciais de teste.
