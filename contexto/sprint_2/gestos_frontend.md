# Gestos no frontend — Sprint 2

## Objetivo

Adicionar interações por gesto às telas de tarefas.

## Alterações

- O detalhe da tarefa volta à lista com arraste horizontal para a direita; o botão de voltar continua disponível.
- Tarefas em aberto atribuídas ao usuário podem ser deslizadas para a esquerda para serem concluídas. As demais não expõem essa ação.
- A raiz do app foi preparada para gestos e o gesto preditivo de voltar foi habilitado no Android.

## Validação

- `npm.cmd run lint` concluído sem erros.
- `npx.cmd tsc --noEmit` concluído sem erros.

## Limitação

- A conclusão por gesto atua sobre os dados de demonstração existentes; não adiciona persistência nem chamadas de API.
