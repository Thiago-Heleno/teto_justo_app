# Criação de tarefas com regras de negócio

## Objetivo

Ajustar `POST /tarefas/` para exigir administrador da casa, peso positivo,
prazo futuro e responsáveis pertencentes à mesma casa.

## Alterações

- `TarefaCriar` passou a exigir `peso` entre 1 e 4 e ao menos um responsável.
- O serviço converte `peso` para a coluna já existente `tarefa.dificuldade`.
- O prazo é validado no backend como futuro, inclusive para datas sem fuso.
- A autorização existente do proprietário da casa continua sendo usada.
- Os responsáveis são conferidos em `pertencer`; o administrador da casa também
  é aceito como membro da própria casa.

## Validação

- Testes unitários direcionados de tarefas e autenticação: 30 aprovados.
- Compilação Python e `git diff --check` executados com sucesso.
