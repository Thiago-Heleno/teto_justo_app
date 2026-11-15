# Navegação compacta na web

## Objetivo

Ajustar a barra de navegação da web (`app-tabs.web.tsx`): remover a moldura
escura ao redor da pílula, e em telas estreitas manter a barra sempre visível,
só com ícones, numa única linha. Também fazer `gerenciar-casa` e `rotatividades`
exibirem a barra, como as demais telas.

## Alterações

`src/frontend/src/components/app-tabs.web.tsx`:

- Removido o botão de menu (hambúrguer/`X`) e o estado `menuAberto`/`recolherMenu`
  que escondia a navegação no modo compacto (`width < 600`). A barra agora fica
  sempre visível. Removidos os estilos `menuHeader`, `menuButton` e `hidden` e
  os ícones `Menu`/`X`.
- Em modo compacto, `TabButton` renderiza só o ícone (o texto fica oculto) e
  recebe `accessibilityLabel` com o rótulo para leitores de tela. O valor de
  compacto é compartilhado por um `CompactoContext`, porque `TabButton` é
  montado como filho de `TabTrigger` e não recebe props diretas.
- `innerContainer` passou de `flexWrap: "wrap"` para `"nowrap"`, evitando a
  quebra de linha. Novo estilo `tabButtonViewCompacto` dá `flex: 1`,
  centralização e padding horizontal menor, para os cinco ícones caberem na
  linha em telas estreitas. Em compacto, o `MotionPressable` (filho direto do
  container flex) também recebe `flex: 1` (`pressableCompacto`), para cada botão
  ocupar fração igual da largura e os ícones se distribuírem pela barra em vez
  de se agruparem à esquerda.
- `tabListContainer` (View externo) recebeu `backgroundColor: Caldera.limestone`.
  Antes era um View sem fundo, então no tema escuro o `background` preto da
  página aparecia como moldura em volta da pílula clara.

Barra em `gerenciar-casa` e `rotatividades`:

- `src/frontend/src/app/gerenciar-casa.tsx` e `rotatividades.tsx` movidos para
  `src/frontend/src/app/(app)/`. O grupo `(app)` tem o `_layout` que renderiza a
  barra; as telas antes ficavam soltas na raiz, fora do grupo, e por isso não a
  exibiam. Os hrefs não mudam, pois grupos de rota não aparecem na URL.
- `src/frontend/src/app/_layout.tsx`: removidas as `Stack.Screen` dessas duas
  rotas, já que passaram a pertencer a `(app)`.
- `app-tabs.web.tsx`: adicionado um `TabTrigger` sem UI (`display: none`) no
  `TabList` para cada uma. Pelo `expo-router/ui`, uma rota do grupo só é
  navegável se tiver `TabTrigger`; sem filhos, ele registra a rota sem virar
  aba visível.
- `app-tabs.tsx` (nativo): adicionado um `NativeTabs.Trigger` para cada
  ("Casa", "Rodízio"). No `NativeTabs`, `hidden` removeria a aba mas bloquearia
  a navegação, então o trigger fica visível com ícone/rótulo.

## Decisões

- O fundo da barra foi fixado em `Caldera.limestone` (claro) para combinar com a
  pílula, que já usava essa cor fixa; a barra continua clara nos dois temas.
- No nativo, as duas rotas viram abas visíveis por limitação do `NativeTabs`
  (não há como registrar rota navegável no grupo sem exibir a aba).
- `calendario` foi mantida fora do grupo (Stack raiz, sem barra). A tela é só um
  `Redirect href="/tarefas"` e não tem link no app: é rota de compatibilidade
  para quem abrir `/calendario` direto. Pôr uma aba que redireciona não faria
  sentido.

## Validação executada

- `npx tsc --noEmit` em `src/frontend`: sem erros.
- `npx eslint --fix` nos arquivos alterados: sem erros.

## Limitações

- Sem verificação visual no navegador ou em aparelho; em particular, não foi
  confirmado no app que a barra aparece em `gerenciar-casa` nem o comportamento
  da nova aba nativa.
- Sem testes automatizados para a mudança.
