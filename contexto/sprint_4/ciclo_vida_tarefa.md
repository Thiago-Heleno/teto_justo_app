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

## Limitações

As chamadas PostgREST continuam sendo transações separadas. A unicidade impede
duplicação de evento e o CAS protege cada atualização, mas não há atomicidade
entre evento, saldo e tarefa. Uma queda ou erro depois de inserir o evento e
antes de ajustar o saldo ainda pode exigir reconciliação; essa limitação já
existia e está sinalizada no código. Não houve migrações ou novas funções no banco.

Testes com Supabase real não foram executados.
