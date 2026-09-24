# Finalização de tarefa no frontend — Sprint 2

## Objetivo

Criar um fluxo inicial para finalizar uma tarefa e mostrar ao usuário um
retorno visual com os pontos recebidos e o novo saldo.

## Implementação

Na tela de detalhes, tarefas pendentes ou atrasadas agora exibem o botão
**Finalizar tarefa**. Durante o processamento, o botão fica desabilitado e
mostra o texto **Finalizando...**.

Ao concluir a operação, o frontend:

1. consulta o saldo atual do responsável;
2. envia um `PATCH /tarefas/{id}` com `estado_atual: "finalizado"`;
3. consulta novamente os moradores da casa;
4. calcula os pontos obtidos pela diferença entre o saldo novo e o anterior;
5. atualiza a tarefa e a quantidade de tarefas em aberto;
6. apresenta um pop-up de parabéns.

O pop-up informa:

- o nome da tarefa finalizada;
- os pontos obtidos;
- o saldo atual do responsável;
- um botão **Continuar**.

Após **Continuar**, o pop-up é fechado e a lista de tarefas é recarregada.
Esse comportamento evita que a tela de detalhes desapareça antes de o usuário
ler o resultado, principalmente quando existe um filtro de tarefas pendentes.

## Arquivos alterados

- `src/frontend/src/services/tarefas-api.ts`: adiciona o campo `score` ao tipo
  `Morador`, suporte a requisições `PATCH` e a função `finalizarTarefa`.
- `src/frontend/src/components/detalhe-tarefa.tsx`: adiciona o botão, os estados
  de carregamento e erro e o pop-up seguindo o visual Caldera.
- `src/frontend/src/app/tarefas.tsx`: coordena a finalização, atualiza os dados
  locais e calcula os pontos creditados.

## Validações realizadas

- ESLint aprovado nos três arquivos alterados.
- Dois testes existentes do frontend aprovados.
- Requisição `PATCH` de finalização validada separadamente.
- A checagem global do TypeScript continua bloqueada por declarações ausentes
  para dois arquivos CSS preexistentes, sem erros apontados nas alterações.

## Limitação atual

O endpoint genérico `PATCH /tarefas/{id}` exige que o usuário autenticado seja
administrador da casa. Por isso, o botão ainda não permite que qualquer
responsável finalize sua própria tarefa.

Como evolução, recomenda-se criar um endpoint específico de finalização que
autorize o responsável e retorne de forma direta e atômica os pontos obtidos e
o saldo atualizado.
