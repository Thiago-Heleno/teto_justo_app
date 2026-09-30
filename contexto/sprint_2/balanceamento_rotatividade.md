# Balanceamento de rotatividade

## Objetivo

Distribuir ocorrências recorrentes entre os moradores de uma casa, respeitando
quem pode executar cada tarefa e aproximando a pontuação potencial acumulada de
cada pessoa.

## Implementação

- `src/backend/services/rotatividade.py` adiciona um serviço puro, sem acesso ao
  Supabase, com modelos imutáveis para tarefas, atribuições e resultado.
- As ocorrências são ordenadas pela maior pontuação potencial e cada uma é
  atribuída ao membro elegível com menor total acumulado.
- A ordem fornecida dos membros resolve empates, tornando o resultado
  determinístico. Pontuações anteriores podem ser informadas para manter o
  equilíbrio entre ciclos.
- Entradas inválidas, membros duplicados, elegibilidade vazia ou pessoa fora da
  casa geram `ValueError` explícito.

## Validação

- `tests/test_servico_rotatividade_unitario.py` cobre balanceamento, restrição de
  elegibilidade, desempate determinístico, pontuação anterior e validações.
- `tests/test_servico_agendamento_rotatividade_unitario.py` cobre o calendário
  das ocorrências e a gravação direta da ocorrência com o responsável escolhido
  pelo balanceador.

## Integração

- `POST /rotatividades/` grava a configuração e a ordem dos participantes pelo
  backend. A interface envia essa configuração quando a API está habilitada.
- `POST /jobs/rotatividades` processa as ocorrências vencidas do calendário,
  aplica `ServicoRotatividade` aos participantes que ainda pertencem à casa e
  grava a tarefa e a atribuição diretamente nas tabelas existentes.
- O job pode recuperar uma ocorrência já criada que ainda não tenha atribuição.
  A unicidade existente por rodízio e data evita criar duas tarefas para a
  mesma ocorrência. O processamento deve ser agendado para rodar diariamente
  com `ROTATIVIDADE_JOB_TOKEN` e em um único worker, pois o bloqueio contra
  execuções simultâneas existe no processo do backend.
- A implementação usa chamadas de tabela do Supabase no backend; não chama
  funções SQL/RPC e não adiciona migrations. Ela requer que o esquema de
  rodízios descrito em `docs/migrations/18.sql` já esteja disponível no banco.
