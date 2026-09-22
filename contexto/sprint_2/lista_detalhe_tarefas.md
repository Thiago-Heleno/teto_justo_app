# Lista e detalhe de tarefas — Sprint 2

## Objetivo

Criar uma demonstração frontend da lista de tarefas da casa, com filtros por
status, responsável e prazo, além do detalhe com descrição, peso, prazo,
responsáveis e status. A conclusão fica disponível somente quando a usuária da
demonstração é uma das responsáveis.

## Arquivos e comportamentos

- `src/frontend/src/app/tarefas.tsx`: nova rota com resumo de tarefas em aberto,
  filtros combináveis, cartões responsivos, estado vazio e abertura do detalhe.
- `src/frontend/src/components/detalhe-tarefa.tsx`: detalhe da tarefa e ação local
  de conclusão; pessoas não responsáveis recebem uma mensagem sem o botão de
  concluir.
- `src/frontend/src/components/motion-pressable.tsx`: feedback reutilizável de
  hover, foco e pressão com escala curta, executado pelo Reanimated.
- `src/frontend/src/data/tarefa-demonstracao.ts`: tarefas fictícias com estados,
  pesos, responsáveis e prazos relativos à data de execução. Os moradores e a
  casa existentes foram reutilizados.
- `src/frontend/src/utils/filtros-tarefa.ts`: filtragem pura e formatação do
  prazo. `scripts/filtros-tarefa.test.mjs` verifica filtros combinados.
- `src/frontend/src/constants/theme.ts` e `constants/tarefa.ts`: tokens Caldera,
  fonte condensada nativa e contratos de estado reutilizados pelas telas.
- `src/frontend/src/components/app-tabs.tsx` e `app-tabs.web.tsx`: acesso à rota
  “Tarefas” e navegação alinhada à identidade visual do produto.
- `src/frontend/package.json`: comando `npm run test:tarefas` para a checagem
  isolada dos filtros, sem nova dependência.

## Decisões técnicas

- O escopo permanece demonstrativo e usa estado local, como a tela de criação
  existente. Concluir atualiza somente a sessão atual; recarregar restaura os
  dados fictícios.
- Foram aplicadas as superfícies Pumice/Limestone, destaque Ember, tags Sulfur,
  tipografia condensada, raios de 40 px e controles pill definidos em
  `DESIGN.md`, sem sombras nem novas cores ou bibliotecas.
- “Prazo vencido” considera datas anteriores ao instante atual e ignora apenas
  tarefas finalizadas. “Próximos 7 dias” considera prazos futuros até sete dias.
- O detalhe foi mantido como componente da própria rota, evitando estado global
  e uma hierarquia adicional de navegação nesta demonstração.
- Entradas, saídas e reorganização usam durações entre 140 e 280 ms, com stagger
  limitado a 160 ms. Todas respeitam a preferência de movimento reduzido do
  sistema e evitam sombras, blur ou loops contínuos.
- `DESIGN.md` passou a registrar a escala de motion e os limites de desempenho
  usados nesta tela.

## Validações executadas

- `node --test scripts/filtros-tarefa.test.mjs`: 1 teste aprovado, cobrindo a
  combinação de status, responsável e prazo.
- `tsc --noEmit`: aprovado após a geração local e ignorada de `expo-env.d.ts`.
- ESLint nos arquivos TypeScript/TSX alterados: aprovado sem erros ou avisos.
- `expo export --platform web`: aprovado; a exportação estática incluiu a rota
  `/tarefas`.
- Navegador web: filtros “Pendente” + “Ana Silva” retornaram uma tarefa; tarefa
  de outra responsável não exibiu ação de conclusão; tarefa atribuída à usuária
  foi concluída e mudou para “Finalizada”. Lista e detalhe foram inspecionados
  visualmente, incluindo largura web de 390 px sem overflow horizontal.
- O console não apresentou erros na rodada funcional. Houve somente o aviso de
  desenvolvimento do Reanimated informando que o dispositivo usa movimento
  reduzido.

## Animações e fluidez — 21/09/2026

- Adicionados feedbacks animados de hover, foco e pressão aos filtros, cartões,
  retorno e conclusão; a seleção dos filtros interpola a cor de fundo.
- A tela anima a entrada geral, o resultado da filtragem, a entrada e saída
  dos cartões, o estado vazio, a transição para o detalhe e a confirmação da
  conclusão. As transições usam transform, opacidade, cor e layout na UI thread.
- `tsc --noEmit`, ESLint dos quatro arquivos TypeScript/TSX alterados, teste dos
  filtros e `expo export --platform web`: aprovados.
- No navegador, filtros combinados retornaram uma tarefa, permissões de conclusão
  foram preservadas, a conclusão mudou o status sem erros no console e a largura
  de 390 px permaneceu sem overflow horizontal.
- A preferência de movimento reduzido estava ativa no ambiente e o Reanimated
  suprimiu as transições visuais. A cadência completa deve ser conferida também
  com movimento reduzido desativado em dispositivo ou navegador de homologação.

## Limitações e pendências

- Não há integração com a API, autenticação ou persistência; essas dependências
  continuam registradas em `pendencias_integracao_tarefas.md`.
- Não houve teste em aparelho ou emulador Android/iOS. Áreas seguras, navegação
  nativa e tecnologias assistivas ainda precisam de validação em dispositivo.
