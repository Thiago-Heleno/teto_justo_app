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
