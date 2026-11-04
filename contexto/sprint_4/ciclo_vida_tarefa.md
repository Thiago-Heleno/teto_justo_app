# Ciclo de vida da tarefa — task 296

## Objetivo

Implementar a candidata 2 de `docs/architecture-review.html`: concentrar estado,
prazo e transições de pontuação no backend, preservando permissões, contratos
HTTP e o cálculo de pontos existente.

## Implementação e decisões

- `src/backend/services/ciclo_vida_tarefa.py` reúne as decisões puras de estado,
  conversão para UTC, janela de dia fixo, filtro por dia da casa e edição de
  prazos. As funções recebem dados e instante explicitamente, sem consultas.
- `ServicoCicloVidaTarefa` concentra sincronização de estado, conclusão e
  reabertura. Crédito e estorno compartilham o registro do evento por tipo/ciclo
  e o ajuste de saldo com até cinco tentativas de compare-and-swap (CAS).
- `ServicoTarefa` mantém autorização, consultas e montagem da resposta;
  `ServicoPenalidade` mantém paginação e contadores do job. Ambos usam a mesma
  transição condicional. Leituras agora também corrigem `pendente` para
  `atrasada` dentro da tolerância, como o job já fazia.
- A sincronização preserva estados finais e só agenda o aviso de prazo
  encerrado quando a própria escrita altera o estado. Se a leitura perde o CAS,
  consulta a versão atual sem sobrescrever uma conclusão concorrente.
- Uma listagem por casa usa o mesmo instante para estado e filtros de prazo.
  O fuso continua vindo da casa; a janela de dia fixo respeita o fuso salvo na
  tarefa/configuração. Placar e agendamento reutilizam a conversão UTC; tarefas
  unitárias e ocorrências de rodízio compartilham a janela de dia fixo.
- A conclusão mantém as condições anteriores do CAS e verifica também o ciclo
  de reabertura. Reabrir preserva a tolerância, estorna apenas o crédito daquele
  ciclo e incrementa o ciclo uma única vez. Vínculo ativo continua obrigatório.
- O frontend permanece inalterado: a lista já envia filtros ao backend e o
  calendário já usa o fuso da casa. A divergência de “hoje” descrita no relatório
  não está presente nesses caminhos atuais; os testes existentes de fusos e
  dias completos foram preservados.

## Validação

Os testes de ciclo de vida reutilizam o banco em memória do contrato de casas,
com unicidade de evento simulada por usuário/tarefa/tipo/ciclo, sem fixar a ordem das
consultas. Cobrem leitura e job, limite exato de tolerância, datas legadas,
fusos, conclusão repetida, estorno repetido, novo ciclo, conflito no saldo e
falha de gravação do evento. Os testes anteriores de permissão e concorrência
permanecem na suíte.

Executado a partir de `src/backend`, com variáveis de Supabase de teste local,
sem serviços externos:

- `python -B -m pytest -q -p no:cacheprovider tests --ignore-glob='*_integracao.py'`:
  **598 testes aprovados**, incluindo os 25 cenários do novo módulo.
- `ruff check . --no-cache`: aprovado.
- `bandit -r . -x ./venv,./tests`: sem apontamentos.
- `git diff --check`, a partir da raiz: aprovado.

Permanece o aviso de depreciação TestClient/httpx já presente antes das mudanças.

## Revisão das candidatas 1 e 2

Aplicadas as orientações Ponytail e uma revisão independente em dois eixos
contra o commit-base `f703950768bc3d9cba71024283893a336dc3b661`, incluindo
alterações locais e arquivos novos:

- Standards: nenhum achado acionável nos padrões documentados ou smells avaliados.
- Spec: nenhum requisito faltante ou regressão identificada em relação ao pedido
  e ao relatório, considerando o estado atual dos chamadores.

A revisão foi estática e complementa os testes executados. `ServicoTarefa`
passou de 761 para 426 linhas; `atualizar_tarefa`, de 145 para 103 linhas.

Na revisão anterior ao commit, a chave de unicidade do banco falso foi alinhada
à migration `26.sql`: inclui usuário, tarefa, tipo e ciclo. Esse ajuste altera
apenas a simulação dos testes; não modifica o código de produção.
Os 25 testes afetados e o Ruff foram reexecutados após o ajuste e aprovados.
As duas revisões confirmaram ausência de achados pendentes.

Na preparação do PR, integrada a `main` até `7de0f90`, preservando os nomes de
tarefas no extrato de pontos. A suíte completa passou com **599 testes** após
a integração; Ruff e Bandit também passaram. Os três arquivos sobrepostos
mantêm as terminações de linha da `main`, sem alterações de formatação no PR.

## Limitações

As chamadas PostgREST continuam sendo transações separadas. A unicidade impede
duplicação de evento e o CAS protege cada atualização, mas não há atomicidade
entre evento, saldo e tarefa. Uma queda ou erro depois de inserir o evento e
antes de ajustar o saldo ainda pode exigir reconciliação; essa limitação já
existia e está sinalizada no código. Não houve migrações ou novas funções no banco.

Testes com Supabase real não foram executados.

## Dia fixo: abertura somente no vencimento

- `janela_dia_fixo`, em `src/backend/services/ciclo_vida_tarefa.py`, passa a
  calcular o início à meia-noite e o vencimento no último microssegundo da
  mesma data, no fuso informado, convertendo ambos para UTC. O cálculo não
  recebe mais `prazo_dias` e não consulta o banco.
- Criação de tarefas em `src/backend/services/tarefa.py`, edição de prazo e
  geração de ocorrências em `src/backend/services/rotatividade_agendamento.py`
  usam essa janela. Editar a data fixa também funciona em registros legados
  sem `prazo_dias`. Intervalos, tolerância de atraso e pontuação foram preservados.
- O contrato HTTP mantém `prazo_dias` por compatibilidade com os clientes;
  esse campo não altera a janela de dia fixo. A remoção de “Dias para terminar”
  no frontend permanece pendente, pois esta alteração se limita ao backend.
- Registros e ocorrências já gravados não são recalculados automaticamente.
  A edição de `data_fixa` ou `prazo_dias` recalcula a janela da tarefa editada;
  executar novamente o job não altera ocorrências existentes. Não há migração.

Validação desta alteração, a partir de `src/backend`, com as variáveis de
Supabase apontando para valores fictícios de teste e sem serviços externos:

- A execução inicial com o Python global encontrou ausência de `tzdata`.
  Foi usado o ambiente virtual existente, sem alterar dependências.
- Antes da correção, os testes de ciclo de vida e agendamento reproduziram
  o defeito: **11 falhas e 32 aprovações**.
- `./venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/test_ciclo_vida_tarefa_unitario.py tests/test_servico_agendamento_rotatividade_unitario.py tests/test_servico_tarefa_unitario.py --tb=short`:
  **151 testes aprovados**. Cobrem fusos (inclusive mudança de horário de
  verão), edição sem depender da duração, bloqueio da conclusão antes da
  meia-noite, liberação na meia-noite e ocorrência de rodízio em dia fixo.
- `ruff check services/ciclo_vida_tarefa.py services/tarefa.py services/rotatividade_agendamento.py tests/test_ciclo_vida_tarefa_unitario.py tests/test_servico_agendamento_rotatividade_unitario.py --no-cache`:
  aprovado. Permanece o aviso preexistente de depreciação TestClient/httpx.
- A tentativa de executar toda a suíte unitária com
  `./venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests --ignore-glob='*_integracao.py' --tb=short`
  ficou sem retornar saída e foi interrompida. Não há resultado da suíte
  completa para esta alteração; a causa não foi investigada.
- `git diff --check`, a partir da raiz do repositório: aprovado.
- O CI (`Backend tests`, suíte de integração com Supabase) reprovou
  `test_tipo_e_modo_prazo_persistem_no_supabase[dia_fixo]`: o teste ainda
  exigia `fim - inicio == 2 dias`, valor do comportamento antigo. O teste foi
  corrigido para conferir, no dia fixo, início à meia-noite e fim em
  `time.max` da `data_fixa` no fuso da casa; a duração de 2 dias vale só no
  modo intervalo. O código de produção não mudou. Essa correção ainda não foi
  executada contra o Supabase real (depende de nova execução do CI).
