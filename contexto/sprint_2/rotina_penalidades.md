# Rotina agendada de penalidades

## Objetivo

Sincronizar tarefas abertas com o vencimento e a tolerância definidos, deixando
uma chamada idempotente disponível para um agendador externo.

## Comportamento

- `POST /jobs/penalidades` exige o cabeçalho `X-Penalidade-Job-Token`, validado
  com o segredo de ambiente `PENALIDADE_JOB_TOKEN`. Sem segredo configurado, a
  rota retorna `503`; token inválido retorna `401`.
- Para desenvolvimento local, cada desenvolvedor gera e usa seu próprio token
  no `.env` não versionado; não é preciso compartilhá-lo entre colegas. Em
  ambiente compartilhado, o mesmo segredo precisa estar no backend e no
  agendador, distribuído somente pelo armazenamento de segredos da equipe.
- `.env.example` mantém a variável sem valor. Nunca commitar ou registrar o
  segredo em frontend, documentação, mensagens ou logs.
- Tarefa dentro do prazo permanece `pendente`; após o vencimento fica
  `atrasada`; ao ultrapassar `atraso_maximo`, passa para `nao_feito`.
- Cada alteração compara estado, vencimento e tolerância atuais, de modo que
  execuções concorrentes não sobrescrevam conclusão ou edição concorrente.
- A rotina não debita saldo nem grava eventos de pontuação. A perda proporcional
  `100 / (atraso_maximo + 1)` por dia é refletida no crédito calculado ao
  concluir; a conclusão existente grava o evento uma única vez.
- A frequência do agendador deve ser configurada fora da aplicação.

## Arquivos

- `src/backend/services/penalidade.py`: consulta paginada e transições
  condicionais das tarefas abertas.
- `src/backend/routers/jobs.py` e `src/backend/schemas/penalidade.py`: endpoint
  interno autenticado e formato da resposta.
- `.env.example` e `README.md`: configuração e instruções de chamada.
- `src/backend/tests/test_servico_penalidade_unitario.py` e
  `src/backend/tests/test_jobs_router_unitario.py`: cobertura com cliente de
  banco simulado e testes HTTP sem banco real.

## Validação

- Suíte unitária do backend: 223 testes aprovados.
- Ruff e compilação Python dos arquivos alterados: aprovados.
- `git diff --check`: aprovado.
- Testes de integração com Supabase não executados; dependem de um ambiente de
  teste configurado.
- A configuração da variável local e a implantação do agendador são
  responsabilidade de cada ambiente; o valor do segredo não é versionado.
