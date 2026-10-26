# Simplificação da aba Pontuação — Sprint 4

## Objetivo e comportamento

Concentrar a consulta de pontos em um único placar e nas movimentações
recentes, reduzindo repetições e a altura da tela.

- Cabeçalho compacto com o total da casa no período selecionado e Atualizar.
- Um único Placar da casa com Semana, Mês, Ano e Acumulado; Semana continua
  sendo a seleção inicial. Os filtros alteram o placar e o total da casa.
- Cada morador aparece com posição, nome e pontos do período. A conta logada
  recebe borda discreta e o texto Você. O saldo acumulado não se repete.
- Como funciona expande as explicações de períodos, fuso da casa e empates.
- Movimentações recentes começa com cinco eventos. Ver mais revela outros
  cinco por clique, até esgotar os eventos carregados. O extrato independe
  do período do placar e preserva créditos, estornos, moradores e datas.
- A quantidade já expandida permanece ao atualizar. A troca de casa recria
  a tela pelo layout existente e restaura os valores iniciais.

## Arquivo e decisões

Alterado `src/frontend/src/app/(app)/pontuacao.tsx`.

Reutilizados `resumirPlacar`, `periodosPlacar`, os componentes e as cores
existentes. Removidos os blocos Classificação/Ranking geral duplicados,
o quadro com todos os períodos e os estilos sem uso.

A tela deixa de consultar o ranking separado e usa o placar existente.
A identidade usa `carregarUsuarioAtual`; falha nessa consulta apenas omite
o destaque pessoal. Falhas do placar/extrato continuam oferecendo nova
tentativa e identificando os dados anteriores. Nenhum contrato de API,
cálculo de pontos, dependência ou banco foi alterado.

## Validação executada

A partir de `src/frontend`:

- `node --test scripts/placar.test.mjs`: três testes aprovados, cobrindo
  ordenação, empate, totais, períodos, valores negativos e casa vazia.
  Houve aviso do Node sobre o tipo de módulo não declarado no pacote.
- ESLint da tela: aprovado. As tentativas de lint completo, pelo script npm
  e pelo executável local, foram interrompidas sem resultado; não contam
  como validação aprovada do projeto inteiro.
- Prettier aplicado à tela.
- `git diff --check`, a partir da raiz: aprovado.
- `node node_modules/typescript/bin/tsc --noEmit`: falhou pela ausência local
  de `expo-notifications` e pelos tipos implícitos associados em
  `src/app/_layout.tsx`. Esses arquivos não foram alterados.
- A tentativa de instalar as dependências declaradas em modo offline falhou
  com `ENOTCACHED` para `@expo/ui`; manifesto e lockfile permaneceram intactos.

## Limitações

- Não houve validação visual no navegador nem em Android/iOS.
- O extrato mantém o limite existente de 100 eventos recentes da API.
  Ver mais expande os dados já carregados; não busca páginas mais antigas.
  Quando há histórico além dos eventos visíveis, a tela informa o total.
