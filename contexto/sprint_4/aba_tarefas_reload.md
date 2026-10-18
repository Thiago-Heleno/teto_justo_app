# Task 260 — recarga da aba Tarefas (Sprint 4)

## Objetivo e comportamento entregue

A aba Tarefas atualiza casa, moradores, usuário, tarefas e placar ao receber foco. O botão **Atualizar** repete as consultas sem sair da aba. Os filtros escolhidos permanecem ativos; quando há filtro, a lista é consultada com esses parâmetros na API. As requisições em andamento são canceladas ao perder o foco ou trocar de casa; a consulta filtrada também é cancelada ao alterar o filtro.

Enquanto a atualização ocorre, o botão indica **Atualizando…**. Se a consulta falhar, a tela mostra o erro e **Tentar novamente**. Dados preservados da última consulta bem-sucedida são identificados como antigos. Resultados de outra casa ou sessão não são exibidos durante a troca. Se a tarefa selecionada deixar de constar da lista após uma recarga, a seleção e a edição são encerradas. A confirmação da conclusão e sua tela de pontuação continuam disponíveis até **Continuar**.

## Redundâncias e correções

- `src/frontend/src/app/(app)/tarefas.tsx`: a consulta sem filtros alimenta a lista padrão e a contagem, eliminando a segunda busca inicial das mesmas tarefas.
- **Em aberto** conta apenas `pendente` e `atrasada`; `nao_feito` não entra na contagem.
- A conclusão, a reabertura e a edição atualizam os dados locais da tarefa. A reabertura e a edição também consultam novamente os dados da aba; após **Continuar**, a conclusão faz a mesma recarga.
- O placar permanece na aba e é atualizado com os demais dados. Uma falha em sua consulta identifica o placar anterior como antigo.

## Validação executada

Comandos executados em `src/frontend`, exceto `git diff --check`, executado na raiz do repositório:

- `npm run test:tarefas`: 53 testes aprovados.
- `npx eslint 'src/app/(app)/tarefas.tsx'`: aprovado.
- `npx tsc --noEmit`: aprovado após o Expo regenerar os tipos locais de rota, incluindo `/calendario`.
- `git diff --check`: aprovado.

Verificação manual na web com API fictícia local: retorno de **Criar** e **Calendário** para Tarefas; botão **Atualizar**; filtro `Pendente` consultado pela API e remoção do filtro sem busca duplicada; falha e recuperação da lista; falha do placar com indicação de dado antigo; contagem com `pendente`, `atrasada` e `nao_feito`; conclusão com confirmação, reabertura e edição; limpeza da tarefa selecionada após ela sumir da API; e troca de casa, com carregamento antes de mostrar os dados da nova casa. A primeira abertura sem filtros produziu uma única chamada à lista de tarefas.

## Limites

- A verificação no navegador usou dados simulados. Não houve execução contra o banco real nem em Android/iOS.
- A atualização acontece ao voltar à aba ou usar o botão; não há sincronização em tempo real enquanto a aba permanece aberta.
- Os 53 testes existentes cobrem serviços e regras, mas não fazem um teste automatizado do ciclo de foco da tela. Esse ciclo foi verificado manualmente na web.
