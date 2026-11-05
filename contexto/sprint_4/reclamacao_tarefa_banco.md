# Reclamação de tarefa: banco, schemas e serviço

## Objetivo

Preparar a base de dados e os schemas da casa e implementar o serviço principal
de reclamação da qualidade de execução de tarefas, com reabertura pelo ciclo de
vida existente.

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
- Pendentes: notificações `tarefa_reclamada` e `tarefa_reaberta`, seletor de
  política na criação e edição da casa e exposição dos metadados de reclamação
  no contrato de tarefa consumido pelo frontend.

## Serviço principal — 2026-11-04

### Arquivos e comportamentos

- `src/backend/services/reclamacao.py`: novo `ServicoReclamacao` valida tarefa
  finalizada, conclusão entre agora e 24 horas atrás (limite inclusivo), vínculo
  ativo na mesma casa, autor diferente do responsável atribuído e política
  diferente de `nenhuma`. Datas sem fuso são tratadas como UTC pelo helper
  existente `instante_utc`.
- A reclamação é gravada com o ciclo de `tarefa.reaberturas`. Violação de
  unicidade retorna HTTP 409; outros erros de persistência são propagados.
- `uma_reclamacao` só registra a reclamação e avisa o responsável a cada
  report; nunca reabre a tarefa. `votacao` conta somente as reclamações daquela
  tarefa no ciclo atual e chama `ciclo_vida.reabrir` ao alcançar o limite.
- `src/backend/routers/tarefa.py`: `POST /tarefas/{id_tarefa}/reclamacoes`
  autenticado, sem corpo, retorna o `TarefaResposta` existente.
- `src/backend/tests/test_reclamacao_unitario.py`: 33 casos de unidade com
  Supabase em memória, incluindo validações, duplicata, ciclos independentes,
  limiar da votação, reabertura e estorno, leitura concorrente e contrato HTTP.

### Decisões técnicas

- Confirmado para esta tarefa: quem não pode reclamar é o responsável em
  `atribuida`, e não o criador da tarefa nem o proprietário da casa. O
  proprietário pode reclamar quando tem vínculo ativo e não é o responsável.
- O limite de votação é metade dos demais moradores ativos da casa,
  arredondando para cima, com mínimo de uma reclamação. O responsável fica
  fora desse total. A consulta usa a paginação existente de autorização e o
  limite é recalculado a cada reclamação; a contagem de reclamações usa
  `count="exact"` para não depender do limite de linhas da API.
- A reabertura não passa pela autorização de administrador de `ServicoTarefa`.
  O ciclo de vida mantém o CAS por `reaberturas`, o estorno único e a decisão
  entre `pendente`, `atrasada` e `nao_feito`, incluindo a tolerância existente.
- Foram reutilizadas as consultas e a montagem de resposta de `ServicoTarefa`.
  Não foram adicionadas migrations, funções SQL ou dependências.

### Validação desta implementação

- A partir de `src/backend`, com as variáveis de Supabase configuradas para
  teste local: `python -m pytest -q tests --ignore-glob='*_integracao.py'` —
  **689 testes aprovados**, com dois avisos de depreciação do TestClient.
- A partir da raiz: `ruff check src/backend/services/reclamacao.py
  src/backend/routers/tarefa.py src/backend/tests/test_reclamacao_unitario.py`
  e `git diff --check` — aprovados.
- Testes de integração com banco real e execução de migrations não realizados.

### Limitações e pendências do serviço

- O frontend atual ainda bloqueia o proprietário da casa e aceita somente
  intervalos menores que 24 horas; precisa ser alinhado à regra confirmada.
- A resposta ainda usa o schema de tarefa atual, sem `politica_reclamacao`,
  `reclamacoes_count` e `reclamacoes_limite`. A integração dos avisos preparados
  em `notificacoes_push.md` também permanece pendente.
- Registro da reclamação e reabertura são operações separadas. Uma falha após
  o registro pode deixar a reclamação persistida sem concluir a reabertura;
  esta entrega não adiciona transação nem retomada automática.
