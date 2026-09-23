# Alinhamento peso (dificuldade) x pontuação

## Objetivo

Corrigir a quebra do teste de integração `test_crud_tarefa_no_supabase` causada pela migration `docs/migrations/13.sql`, que passou a restringir a coluna `dificuldade` (peso) a `1, 2, 3` no Supabase real. O teste e o schema Pydantic ainda esperavam `peso` até `4`, então o PATCH com `peso: 4` violava a constraint `CK_Tarefa_dificuldade` no banco e o erro chegava como 500 não tratado.

## Alterações

- `src/backend/schemas/tarefa.py`: `TarefaCriar.peso` e `TarefaAtualizar.peso` passam de `Field(gt=0, le=4)` / `Literal[1, 2, 3, 4]` para `Literal[1, 2, 3]`, alinhado à constraint do banco e ao `ServicoScore` (`_PONTOS_POR_PESO` só cobre 1-3).
- `src/backend/tests/test_tarefas_integracao.py`: o PATCH do teste de CRUD passa a usar `peso: 3` em vez de `4`.

## Decisão técnica

A coluna `pontuacao` da tabela `tarefa` foi mantida por decisão explícita (ainda é usada pelos testes existentes) — só o trigger de crédito (`fn_tarefa_finalizada_credita_pontos`, migration 13) passou a derivar os pontos-base de `dificuldade` em vez de `pontuacao`. Isso deixa `pontuacao` como coluna não utilizada pelo cálculo real; não foi removida nesta etapa.

Não foi adicionado tratamento genérico de erro de constraint do Postgres no serviço (`ServicoTarefa`): como a validação Pydantic agora rejeita `peso` fora de `1-3` antes da requisição chegar ao Supabase, o 500 relatado deixa de ocorrer sem precisar desse tratamento adicional.

## Validações executadas

Nenhum teste foi executado localmente nesta sessão (sem ambiente Python configurado na máquina no momento da alteração). A mudança foi conferida por leitura do diff e checagem cruzada com `grep` para confirmar que nenhum outro teste usa `peso: 4`. Falta rodar `pytest` (unitários e de integração) para confirmar.

## Pendências

- Rodar a suíte de testes do backend (unitária e de integração) para confirmar a correção.
- Migration 13 ainda não elimina a coluna `pontuacao`; alinhamento completo fica pendente de decisão futura (ver `contexto/sprint_2/documentacao_sistema_pontuacao.md`).
