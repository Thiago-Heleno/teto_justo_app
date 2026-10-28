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

## ECH-304 — lista em blocos e filtro Em aberto

A lista ordena todos os resultados antes de renderizar os primeiros 12 cartões.
**Carregar mais** revela mais 12 por clique e desaparece no último bloco. A
contagem informa **Exibindo X de Y resultados**. A troca de estado, responsável,
prazo, casa ou sessão reinicia o limite em 12; atualizar a mesma consulta e
voltar dos detalhes preservam o limite já ampliado.

O filtro **Em aberto** reúne `pendente` e `atrasada`, combinado com responsável
e prazo. O padrão continua sendo todos os estados nos próximos 7 dias, incluindo
pendências anteriores. `GET /tarefas/casa/{id_casa}` aceita `estado=em_aberto`;
o serviço aplica esse filtro depois da sincronização do estado. O tipo e a
filtragem local do frontend seguem a mesma regra, sem adicionar um estado
persistido nem alterar o formato da resposta.

### Validação desta alteração

- Em `src/backend`, `venv/Scripts/python.exe -m pytest tests/test_servico_tarefa_unitario.py tests/test_listagem_tarefa_router_unitario.py -q`: **109 testes aprovados**. Cobrem a composição dos filtros após sincronização, aceitação de `em_aberto`, encaminhamento dos parâmetros e autorização, além da rejeição de estado inválido com 422.
- Em `src/frontend`, `npm run test:tarefas`: **85 testes aprovados**, incluindo filtragem local e envio de `em_aberto` com a credencial da sessão.
- Em `src/frontend`, `npx tsc --noEmit` e ESLint nos dois arquivos TypeScript alterados: **aprovados**. Os scripts de teste são ignorados pela configuração do ESLint; os quatro arquivos JavaScript/TypeScript alterados foram formatados com Prettier.
- Ruff nos quatro arquivos Python alterados e Bandit nos dois arquivos Python de produção alterados: **aprovados**. A formatação do teste novo foi conferida; o serviço e o teste de serviço já apresentavam diferenças de formatação em `HEAD`, preservadas fora do escopo.
- Exportação estática web com Expo: **aprovada**. Verificação no Chrome com API fictícia local: listas com 0, 12, 13 e 105 resultados; sequência 12/24/36/48/60/72/84/96/105 sem cartões duplicados; ordenação antes do recorte; desaparecimento do botão no último bloco; filtro Em aberto combinado com responsável e prazo; reinício ao trocar filtros/casa; preservação ao atualizar e voltar dos detalhes; conclusão removendo a tarefa de Em aberto e reabertura devolvendo-a à lista.
- `git diff --check`, na raiz do repositório: **aprovado**.

### Limites desta alteração

- Os blocos limitam a renderização, sem paginação na API: todas as tarefas continuam sendo transferidas para alimentar contagem e calendário.
- Os dados da verificação web foram simulados; não houve acesso ao Supabase real nem execução em Android/iOS. As tentativas de captura de tela do Chrome expiraram, por isso não há registro visual dessa verificação.
