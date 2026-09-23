# Integração da lista de tarefas

## Objetivo

Substituir os exemplos locais da rota `/tarefas` por dados da API FastAPI.

## Alterações

- `src/frontend/src/app/tarefas.tsx` carrega casa, moradores e tarefas da casa
  configurada; status, responsável e prazo são enviados para
  `GET /tarefas/casa/{id_casa}`.
- `src/frontend/src/services/tarefas-api.ts` centraliza as chamadas autenticadas
  e os contratos de leitura usados pela lista e pelo detalhe.
- A tela trata carregamento, falha e nova tentativa. A conclusão local foi
  removida, pois não era persistida e a autorização atual do backend não a
  suporta para o responsável.
- `src/backend/main.py` habilita CORS para origens locais configuráveis por
  `CORS_ORIGINS`.
- O README descreve `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_CASA_ID` e
  `EXPO_PUBLIC_TETO_JUSTO_TOKEN` para desenvolvimento local.
- `src/frontend/.env.local` foi criado com os valores de exemplo solicitados;
  como o arquivo é ignorado pelo Git, cada ambiente pode substituí-los pelos
  IDs e token válidos.
- Foi criado no Supabase um usuário, uma casa, o vínculo de morador e uma
  sessão exclusivos do desenvolvimento; a sessão expira 30 dias após a criação.
- `src/backend/core/database.py` também aceita `SUPABASE_SECRET_KEY`, nome
  presente no ambiente local, como alternativa a `SUPABASE_KEY`.

## Validação

- `npx.cmd tsc --noEmit`: aprovado.
- `node --test --test-isolation=none scripts/filtros-tarefa.test.mjs scripts/tarefas-api.test.mjs`:
  2 testes aprovados.
- `npx.cmd eslint` nos arquivos TypeScript alterados: aprovado.
- `git diff --check`: aprovado.
- Criação e leitura de volta da sessão de desenvolvimento no Supabase:
  aprovadas.
- `core/database.py` compilado com `py_compile`: aprovado.
- Após corrigir o e-mail do usuário de desenvolvimento para um domínio válido,
  `GET /tarefas/casa/{id}` com a sessão configurada retornou `200`; o
  preflight CORS de `http://localhost:8081` também retornou `200`.
- A API confirmou o nome UTF-8 do morador de desenvolvimento após corrigir a
  carga inicial que o havia gravado com codificação inválida.

## Pendências

- Ainda não há login e armazenamento seguro de sessão no frontend; o token é
  apenas configuração local de desenvolvimento e não deve ser distribuído.
- A validação contra uma API/Supabase real depende de token e IDs válidos.
- O backend não estava em execução em `127.0.0.1:8000` nesta sessão; iniciar a
  API ainda é necessário antes de abrir a tela no app.
