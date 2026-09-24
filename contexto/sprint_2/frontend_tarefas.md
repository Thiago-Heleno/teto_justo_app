# Frontend de criação de tarefas — Sprint 2

## Rotatividade e consulta de moradores — 24/09/2026

A aba **Criar** agora permite escolher uma tarefa comum ou rotativa. O rodízio
recebe pelo menos dois moradores diferentes, uma ordem ajustável e um ou mais
dias da semana para repetição a cada 1, 2, 3 ou 4 semanas (padrão: 1).
Quatro semanas significam 28 dias, aproximadamente um mês. O primeiro
participante é o responsável inicial;
o prazo de execução de 1 a 5 dias permanece separado da recorrência semanal.

- `src/frontend/src/app/nova-tarefa.tsx`: seleção múltipla acessível, botão
  para antecipar participantes, dias da semana, mensagens de validação, resumo e
  limpeza de todos os campos ao iniciar outra tarefa.
- `src/frontend/src/constants/tarefa.ts`: `rotatividade` guarda participantes
  ordenados, `dias_semana` (1 = segunda-feira a 7 = domingo) e
  `intervalo_semanas` (1 a 4), separadamente de
  `usuarios_atribuidos`, que continua
  contendo apenas o responsável inicial.
- `src/frontend/src/utils/criacao-tarefa.ts`: concentra a preparação e a
  validação dos dados, sem acesso ao banco ou regras de pontuação. Uma tarefa
  comum descarta os campos de rodízio mesmo após alternar entre os tipos.
- `src/frontend/src/services/tarefas-api.ts`: a tela reutiliza as consultas de
  casa e moradores já usadas pela lista. Havendo configuração da API, carrega
  os dados reais com tratamento de carregamento, erro, nova tentativa e casa
  sem moradores. Sem configuração, mantém a demonstração. Em caso de falha,
  dados fictícios só são usados após escolha explícita na tela.

### Regra provisória e limite da entrega

A proposta discutida é manter uma atividade fixa com uma nova ocorrência por
repetição nos dias escolhidos, passando ao próximo participante e preservando as anteriores para
pontuação e histórico. O grupo ainda pode rever essa regra. A configuração
não depende de um mecanismo de geração, facilitando essa alteração futura.

O formulário produz apenas uma **prévia em memória** e informa isso na tela.
Não grava tarefas ou rodízios, não gera ocorrências automaticamente e não
altera a pontuação. A integração desta entrega é de leitura. Nenhuma migration
ou alteração de banco foi aplicada.

Antes da gravação, definir com o grupo a relação entre prazo de execução e
recorrência semanal, a tolerância de atraso, o fechamento de ocorrências não concluídas
e o mecanismo de geração dos próximos períodos. A tabela de atribuições atual
representa responsáveis simultâneos; não deve receber todos os participantes
do rodízio como responsáveis pela mesma ocorrência.

### Validação desta implementação

- Treze testes automatizados aprovados: regras de criação, preservação da ordem,
  dias semanais, moradores inválidos/duplicados, campos obrigatórios, tarefa comum,
  filtros e requisições da API com respostas simuladas.
- TypeScript sem emissão e ESLint dos arquivos TypeScript alterados aprovados.
- Fluxo web conferido com API simulada: seleção/remoção, reordenação, erros,
  resumo, limpeza dos campos, tarefa comum, falha, nova tentativa e escolha
  explícita da demonstração. Layout conferido em 320, 390 e 1280 px.
- Sem validação em aparelho físico ou contra Supabase real nesta entrega.

## Histórico da criação — 22/09/2026

Tela demonstrável de criação, com dados fictícios e estado local. Não há
chamadas à API, gravação ou crédito de pontos. A aba **Criar** abre
`/nova-tarefa`; a listagem tem exemplos independentes e ainda não recebe
as tarefas criadas pelo formulário.

A revisão atual substitui as regras anteriores de seleção múltipla e prazo
por data/hora. O peso possui somente três níveis.

## Regras e comportamento

- Nome obrigatório, rejeitando texto vazio ou apenas espaços; descrição
  opcional e com múltiplas linhas.
- Peso obrigatório, com opções 1, 2 e 3 como dificuldade. Sem conversão
  automática para pontuação.
- Prazo obrigatório, selecionado entre 1 e 5 dias inteiros. Os campos de
  data e horário foram removidos.
- Exatamente um morador responsável, identificado por ID. Escolher outro
  substitui a seleção; tocar novamente no atual mantém a seleção única.
- Nenhum peso, prazo ou responsável começa selecionado.
- Erros próximos aos campos preservam os valores. Envio válido mostra
  “Tarefa criada nesta demonstração” e resumo com um único responsável,
  peso e quantidade de dias. “Criar outra tarefa” limpa todos os campos.

## Arquivos e decisões técnicas

- `src/frontend/src/app/nova-tarefa.tsx`: formulário e confirmação com
  paleta Caldera já existente no projeto: fundo Pumice, cartões Limestone,
  ação e seleção Ember com texto Obsidian, selo Sulfur, cartões de raio 40
  e controles arredondados, sem sombras.
- A tela mantém a apresentação clara definida em `DESIGN.md`, independente
  do tema do dispositivo. Reaproveita `CompactFont` e fonte de corpo da
  plataforma, com peso 500, como as outras telas de tarefas. Os arquivos de
  PP Neue Corp Compact/DM Sans não estão incluídos no repositório; a
  tipografia exata do documento ainda depende desses assets ou substitutos
  aprovados.
- Reutilizado `MotionPressable`, com resposta ao toque e preferência de
  movimento reduzido. Mantidos área segura, rolagem, adaptação ao teclado,
  rótulos e seleção visual que não depende somente de cor. Radios usam
  `accessibilityState` e `aria-checked`; o segundo foi necessário para o
  navegador anunciar a seleção nesta combinação de dependências.
- `src/frontend/src/constants/tarefa.ts`: opções/tipos de peso e dias;
  modelo mínimo com `nome`, `descricao`, `peso`, `prazo_dias` e
  `usuarios_atribuidos: [string]` (um ID). Mantém nomes existentes quando
  aplicáveis; não simula um contrato de API já integrado.
- Removido `src/frontend/src/utils/prazo-tarefa.ts`, cujo validador de data
  e hora deixou de ter consumidores. A demonstração guarda os dias sem
  calcular `data_fim`; a regra de conversão fica para a integração.
- `src/frontend/src/data/tarefa-demonstracao.ts`: mantidos casa e três
  moradores; exemplos da lista agora têm um único responsável e seu tipo
  expressa essa restrição.
- `src/frontend/src/components/detalhe-tarefa.tsx`: identificação de
  responsável no singular. A lista e os filtros continuam usando
  `data_fim` dos exemplos para representar vencimento/atraso; a retirada
  de data/hora se aplica ao formulário de criação.
- README e tutorial de execução atualizados para os campos atuais e a
  aba **Criar**. Pendências de integração revisadas conforme o backend
  presente no repositório. Nenhuma dependência nova foi adicionada.

## Validação desta revisão

- `npx tsc --noEmit`: aprovado.
- ESLint nos quatro arquivos TypeScript alterados: aprovado.
- `npm run lint` foi iniciado, mas interrompido ao percorrer artefatos
  locais gerados. A execução com exclusão de `dist/**` e `android/**`
  concluiu com 1.651 erros de formatação em 21 arquivos existentes, incluindo
  quebras CRLF e `expo-env.d.ts`. Não houve reformatação geral.
- O teste de filtros existente passou com
  `node --test --test-isolation=none scripts/filtros-tarefa.test.mjs`
  (1 teste). O comando padrão `npm run test:tarefas` falhou no sandbox
  com `spawn EPERM`; a alternativa executou o mesmo teste sem subprocesso.
  Não foi adicionada infraestrutura de testes.
- Conferência interativa web: envio vazio, nome apenas com espaços,
  preservação de escolhas após erro, troca de peso, seleção exclusiva
  Ana → Bruno e Ana → Carla, toque repetido mantendo Carla selecionada,
  prazos mínimo de 1 e máximo de 5 dias, descrição opcional e multilinha,
  resumo correto e limpeza para outra tarefa. A árvore de acessibilidade
  confirmou seleção única e ausência dos campos de data/hora e peso 4.
- Conferência visual no navegador em largura padrão e em 390 px; resumo
  também conferido em 320 px, com rolagem e quebra de texto.
- Navegação Criar → Tarefas → detalhe → Criar conferida; o detalhe de
  “Limpar a cozinha” exibiu somente Ana como responsável.
- `git diff --check`: aprovado.

Os registros anteriores de exportação Android/iOS e validação de datas
pertencem à versão anterior. Nesta revisão não foi feita compilação nativa
nem teste em aparelho ou emulador.

## Navegação mobile — 21/09/2026

- Removida `src/frontend/src/app/explore.tsx` e suas referências da navegação
  nativa e web.
- Reduzida a barra inferior para três destinos, com rótulo curto e símbolos
  nativos (`house`, `plus.circle` e `checklist`) em vez de imagens genéricas.
- Ativados `tabBarRespectsIMEInsets` e `disableTransparentOnScrollEdge` para
  evitar que o teclado cubra a barra ou que ela desapareça durante rolagem.
- `npm run lint`: aprovado. `tsc --noEmit -p src/frontend/tsconfig.json`:
  aprovado. Não foi possível validar o toque e a aparência em dispositivo
  físico nesta sessão; o comando `npm run ios` também não está disponível no
  ambiente Windows atual.

## Resolução dos conflitos do PR #54

- Incorporada a `main` em `frontend-tarefa`, preservando navegação, lista,
  filtros, design e alterações de backend recebidas do grupo.
- Resolvidos os conflitos deste resumo, `detalhe-tarefa.tsx`,
  `constants/tarefa.ts` e `data/tarefa-demonstracao.ts`. Também removidos
  marcadores de um stash que haviam sido incluídos no commit da branch.
- Mantidos peso 1..3, prazo 1..5 dias e exatamente um responsável. Os
  tipos/estados da listagem e os imports dos dados fictícios foram preservados.
- Validações desta resolução: TypeScript sem emissão, ESLint dos quatro
  arquivos do fluxo, teste existente de filtros sem isolamento de processo
  e `git diff --check` aprovados; busca por marcadores sem ocorrências.
  O lint inicialmente apontou quebras CRLF nos arquivos do fluxo; eles foram
  normalizados com Prettier, sem reformatação geral do projeto.
- Não houve nova validação em navegador, aparelho ou banco nesta resolução.

## Pendências reais

- Validar teclado virtual, áreas seguras, toque, VoiceOver e TalkBack em
  Android e iOS. A conferência responsiva no navegador não substitui isso.
- Alinhar tipografia distribuída com o grupo e resolver formatação geral
  fora desta alteração.
- Integrar após ajustar contrato: backend ainda aceita peso 4 e vários
  responsáveis, exige `data_fim`, pontuação e atraso máximo. O novo prazo
  de execução de até 5 dias não é `atraso_maximo`. Detalhes em
  [pendencias_integracao_tarefas.md](pendencias_integracao_tarefas.md).
- Definir a contagem dos dias e o efeito de uma futura edição no prazo;
  não foi implementada edição de tarefas existentes.

Execução local: [tutorial_execucao_frontend.md](tutorial_execucao_frontend.md)
e [README da raiz](../../README.md#3-inicie-o-frontend).
