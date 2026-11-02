# Reclamação de tarefa: banco e schemas da casa

## Objetivo

Preparar a base de dados e os schemas da casa para a política de reclamação da
qualidade de execução de tarefas. Esta etapa não cria rota, serviço nem
notificação; esses itens ficam para as etapas seguintes.

## Alterações

- `docs/migrations/33.sql`:
  - `casa.politica_reclamacao` (`TEXT NOT NULL`, default `nenhuma`) com `CHECK`
    para `nenhuma`, `uma_reclamacao` e `votacao`. Casas existentes continuam
    sem reclamação.
  - Tabela `reclamacao_tarefa` com `fk_tarefa_id`, `fk_usuario_id`, `ciclo`,
    `descricao` (opcional, até 500 caracteres) e `criada_em`.
  - `UNIQUE (fk_tarefa_id, fk_usuario_id, ciclo)`: impede reclamar duas vezes no
    mesmo ciclo e reinicia a contagem quando a tarefa é reaberta, já que `ciclo`
    acompanha `tarefa.reaberturas`.
- `src/backend/schemas/casa.py`: `PoliticaReclamacao` (`Literal`) em
  `CasaCriar` (default `nenhuma`), `CasaAtualizar` (opcional) e `CasaResposta`.
  Valor fora dos três é rejeitado pelo próprio tipo.
- `src/backend/services/casa.py`: `_montar_resposta` monta a resposta campo a
  campo e passou a devolver `politica_reclamacao` (fallback `nenhuma`, como o
  `timezone`). Sem isso, `CasaResposta` falharia em toda rota de casa.
- `src/backend/tests/test_servico_casa_unitario.py`: fixture e testes de
  `insert` passam a incluir o campo; testes novos para o default e para valor
  inválido em `CasaCriar` e `CasaAtualizar`.
- `src/backend/tests/test_contrato_casa_router_unitario.py`: o banco em memória
  e os dois conjuntos exatos de chaves da resposta passam a incluir o campo.
- `src/backend/tests/test_casa_integracao.py`: afirma o default `nenhuma` na
  criação (exige a migration `33` aplicada no banco usado).

## Decisões técnicas

- Sem função SQL: só DDL (`CHECK` e `UNIQUE`), conforme a decisão de manter a
  lógica nos serviços Python.
- `fk_tarefa_id` usa `ON DELETE CASCADE`: o serviço só exclui tarefas que não
  estão finalizadas, e só tarefa finalizada recebe reclamação.
- `descricao` entrou para o morador explicar o que não gostou; é opcional para
  não dificultar o report.

## Validação

- `python -m pytest tests -q --ignore-glob='*integracao*'`, a partir de
  `src/backend` — **649 testes aprovados**. Os testes de integração não foram
  executados (exigem banco real).
- A migration não foi executada em banco; o SQL não foi validado contra o
  Supabase.

## Limitações e pendências

- A migration `33.sql` precisa ser aplicada no banco por quem administra o
  Supabase.
- O frontend de reportar (`reportar_tarefa_frontend.md`) envia
  `POST /tarefas/{id}/reclamacoes` sem corpo e espera `politica_reclamacao`,
  `reclamacoes_count` e `reclamacoes_limite` na tarefa. A `descricao` ainda não
  faz parte desse contrato e exige campo de texto no app e aceite no endpoint.
- Pendentes: endpoint e serviço de reclamação (janela de 24h, limite da
  votação, reabertura), notificações `tarefa_reclamada` e `tarefa_reaberta`, e
  seletor de política na criação e edição da casa.
- Decisões em aberto: limite da votação (metade exata ou metade − 1, e se o dono
  conta), recálculo do limite quando moradores entram ou saem, e se o autor da
  reclamação fica visível ao dono da tarefa.
