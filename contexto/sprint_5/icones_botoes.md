# Ícones nos botões

## Objetivo

Adicionar ícones aos botões de ação do app (frontend), sem poluir elementos de seleção.

## Alterações

Biblioteca: `lucide-react-native`, que já era dependência do projeto. Nenhuma dependência nova.

- Botões com ícone passaram a usar `flexDirection: "row"`, `alignItems: "center"` e `gap` no estilo do botão.
- `src/frontend/src/components/gerenciamento-ui.tsx`: o componente `Acao` ganhou a prop opcional `icone`. Os botões de Gerenciar casa, Regras de rodízio e do formulário de rodízio a usam.
- `app-tabs.web.tsx`: as abas da web ganharam ícones, como as abas nativas já tinham. `TabButton` recebe a prop `icon`.
- Setas de texto foram trocadas por ícones: "→" em Ver tarefas, Ver detalhes e card da casa; "▴▾" em Filtros; "‹ ›" no calendário.
- Telas e componentes alterados: início, tarefas, pontuação, nova tarefa, editar tarefa, detalhe da tarefa, calendário, login, cadastro, verificação de e-mail, recuperar e redefinir senha, seleção/criação/entrada de casa, perfil, convidar morador, moradores da casa, detalhes da casa, gerenciar casa e rodízio.

## Decisões

- Sem ícone: campos de escolha (peso, prazo, dias da semana, moradores no formulário), pílulas de filtro, botões de período do placar e cartões de tarefa ou movimentação.
- Cores: ícone na mesma cor do texto do botão (`Caldera.obsidian`, ou `Caldera.chalk` em botão primário escuro). Ações destrutivas usam o vermelho do texto (`#a32316`).

## Validação executada

- `npx tsc --noEmit` em `src/frontend`: sem erros.
- `npx prettier --write` nos arquivos alterados.
- `eslint` apresentou erros de formatação (`prettier/prettier`) em quase todos os arquivos, inclusive nos não alterados. Não foi investigado.

## Limitações

- Não foi feita verificação visual no app (web, Android ou iOS).
- Sem testes automatizados para esta mudança.
