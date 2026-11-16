# ECH-344 · Janela do job de rodízios

## Decisão

- O [agendamento](../../src/backend/services/rotatividade_agendamento.py)
  verifica de hoje até hoje + 60 dias no fuso salvo no rodízio, com os dois
  dias inclusos. A `semana_ancora` continua definindo a cadência. Um rodízio
  diário percorre até 61 datas, independentemente da idade da configuração.
- A consulta de ocorrências usa o começo de hoje e o começo do 61º dia
  seguinte como limites em UTC. O limite final é exclusivo. Cada meia-noite
  é convertida separadamente para acomodar mudanças no deslocamento UTC.
- O job cria as datas faltantes e repara as atribuições incompletas dentro
  da janela. O contador acompanha novas ocorrências. Lacunas anteriores a
  hoje ficam fora do job diário. O balanceamento ainda lê o histórico quando
  precisa atribuir uma ocorrência.

## Validação

- Em `src/backend`, passaram 51 testes unitários de agendamento e das rotas
  do job. A regressão cobre cadência quinzenal, âncora tardia, janela de 61
  datas atravessando uma mudança de horário de verão, lacunas, reparo de
  atribuição e reexecução.
- A suíte do backend sem os testes de integração passou com 760 testes.
- Ruff aprovou lint e formatação dos dois arquivos Python alterados.
- A integração com Supabase descartável permanece pendente.
