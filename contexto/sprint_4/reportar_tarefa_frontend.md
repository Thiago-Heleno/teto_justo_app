# Reportar tarefa no frontend

## Objetivo

Adicionar a ação de reportar uma tarefa finalizada no frontend, conectada ao
contrato futuro de reclamações. A implementação não cria rota, serviço ou
alteração de banco no backend.

## Alterações

- A tela de detalhe exibe `Reportar` somente para moradores que não são o dono
  da casa, quando a tarefa está finalizada, foi concluída há menos de 24 horas
  e `politica_reclamacao` não é `nenhuma`.
- O botão usa `TriangleAlert` de `lucide-react-native` e mostra
  `reclamacoes_count/reclamacoes_limite`.
- O frontend chama `POST /tarefas/{id}/reclamacoes` sem corpo e substitui a
  tarefa local pelo retorno da API.
- Erros retornados em `detail` continuam sendo exibidos pela mensagem padrão de
  `requisitar`.

## Contrato esperado

A tarefa retornada pela API inclui `politica_reclamacao`,
`reclamacoes_count` e `reclamacoes_limite`. As políticas previstas são
`nenhuma`, `uma_reclamacao` e `votacao`.

## Validação

- `npm run test:tarefas`, a partir de `src/frontend` — **88 testes aprovados**.
- `npx prettier --check` nos arquivos novos — aprovado.
- `git diff --check`, a partir da raiz — aprovado.
- `npx tsc --noEmit`, a partir de `src/frontend` — ainda falha em erros
  preexistentes de tipos de rotas em outras telas; não houve erro nos arquivos
  alterados nesta tarefa.
- O lint global também mantém falhas preexistentes de normalização CRLF em
  arquivos do frontend.

## Limitações

A rota ainda não existe no backend nesta etapa; até sua implementação, a ação
pode retornar erro da API. O frontend apenas consome o contrato definido.
