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

## Integração com autenticação

- `GET /usuarios/eu` retorna a pessoa autenticada pela sessão atual.
- A tela de tarefas consulta esse dado junto da casa, moradores e tarefas; o
  botão **Finalizar tarefa** só aparece para quem está atribuído à tarefa.
- O `PATCH /tarefas/{id}` com apenas `estado_atual: finalizado` permite a
  conclusão por um responsável. As demais alterações seguem restritas ao
  administrador da casa, e a API rejeita nova conclusão de tarefa finalizada
  ou não feita.
- O saldo mostrado no pop-up é o do usuário autenticado, em vez do primeiro
  responsável da lista.

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

## Validação da integração

- `npm run test:tarefas`: 14 testes aprovados, incluindo as requisições de
  contexto, usuário atual e finalização.
- `tsc --noEmit`, ESLint direcionado e Prettier dos arquivos frontend
  alterados: aprovados.
- A sintaxe dos arquivos Python alterados foi compilada com `py_compile`.
- Os testes Pytest e Ruff do backend não foram executados: o ambiente virtual
  disponível não possui as dependências de teste e o outro ambiente local
  referencia uma instalação Python sem acesso.
