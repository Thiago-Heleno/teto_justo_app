# Autorização por casa — task 296

## Objetivo

Centralizar as decisões de cargo e acesso no backend, preservando as permissões
e os contratos HTTP existentes.

## Implementação e decisões

- `src/backend/services/autorizacao.py`: a função pura `papel_na_casa` recebe
  usuário, proprietário e a existência de vínculo ativo, normaliza os IDs com
  `str` e retorna `administrador`, `morador` ou `nenhum`. O proprietário tem
  precedência sobre o vínculo. As verificações de acesso e administrador
  reutilizam essa decisão; consultas e erros HTTP permanecem no módulo.
- `src/backend/services/placar.py` e `src/backend/routers/casa.py`: removida a
  autorização duplicada do placar. As seis rotas de leitura de casa, moradores,
  placar, saldo, extrato e ranking usam `ServicoAutorizacaoCasa`.
- `src/backend/services/casa.py`: a listagem reutiliza `ids_casas_acessiveis` e
  `registros_por_ids`, preservando deduplicação, ordenação por ID e paginação
  depois do filtro de acesso. Removida a descoberta duplicada de casas acessíveis.
- A entrada por convite e a saída em `src/backend/services/pertencer.py`
  reutilizam a decisão de administrador com dados já carregados, preservando
  os erros específicos de convite inválido (`400`) e saída do proprietário (`409`).
- Acesso de proprietário não substitui vínculo ativo. Permanecem nos módulos
  atuais as regras de crédito, estorno, reabertura, reentrada e elegibilidade do
  rodízio, incluindo seus filtros de concorrência. A validação de responsáveis
  continua aceitando o proprietário sem vínculo ativo.

## Testes e validações

- Cobertos cargo com IDs em UUID/texto, proprietário sem vínculo, vínculo
  inativo, acesso negado e casa inexistente. Os testes de autorização saíram do
  placar; os de saldo, histórico e auditoria foram preservados.
- Ampliada a matriz HTTP de consultas de score para incluir placar, morador
  inativo e proprietário sem vínculo ou com vínculo inativo.
- A listagem foi exercitada também com páginas e lotes pequenos, atravessando
  múltiplas consultas antes de paginar a resposta.
- Testes confirmam que o proprietário sem vínculo ativo não recebe pontos nem
  se torna elegível para o rodízio. A suíte mantém a restrição de reabertura de
  tarefa com responsável sem vínculo ativo.

Executado a partir de `src/backend`, com `SUPABASE_URL` e `SUPABASE_KEY` de
teste local, sem serviços externos:

- `python -B -m pytest -q -p no:cacheprovider tests --ignore-glob='*_integracao.py'`:
  **573 passaram**. Um aviso de depreciação do TestClient/httpx já aparecia na
  validação anterior à implementação.
- `ruff check . --no-cache`: sem erros.
- `bandit -r . -x ./venv,./tests`: sem apontamentos.

## Limitações

Não foram executados testes com Supabase real. Não houve alterações no frontend,
no schema, nos contratos HTTP ou no tratamento de fuso horário.
