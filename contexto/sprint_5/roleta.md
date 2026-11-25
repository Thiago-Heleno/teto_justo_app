# ECH-337 · Roleta de responsáveis

A criação de tarefas avulsas e a edição apenas da atribuição aceitam sorteio
por administrador ou morador ativo da casa. A edição de outros campos requer
permissão de administrador. O giro pela edição vale para tarefas abertas.

- **Conferir detalhes** valida o formulário e mostra a roda. **Girar a
  roleta** envia `modo_atribuicao: "aleatorio"` sem `usuarios_atribuidos`
  no POST ou PATCH existente. Após a confirmação, a tela mostra que a tarefa
  foi salva.
- A mesma roda atende os dois formulários. Ela usa a lista de moradores e, se
  necessário, o perfil autenticado do administrador. Com dois ou mais
  candidatos, o clique explícito inicia o giro, inclusive com movimento
  reduzido. A roda desacelera sobre a fatia do ID devolvido pelo servidor.
  Com candidato único, a tela exibe a atribuição assim que a resposta chega.
  Um ID ausente da lista local aciona uma atualização dos moradores.
- Em caso de falha de rede durante o salvamento, a tela mantém o formulário e
  orienta a conferir a lista antes de reenviar.

## Validação

- A partir de `src/frontend`, `npm run test:tarefas` passou com 104 testes, e
  `npx tsc --noEmit` e o ESLint dos arquivos alterados passaram.
- A exportação Expo para Web concluiu. No Chrome com API simulada, foram
  conferidos a abertura da conferência sem gravação, o giro durante a
  requisição, o clique duplo, o responsável após recarga, o candidato único,
  o movimento reduzido, a lista desatualizada, a falha de rede e a
  visibilidade por permissão.
- O lint geral com a configuração padrão acusou finais de linha CRLF em
  arquivos preexistentes e formatação no arquivo gerado `expo-env.d.ts`.
- A interação em dispositivo Android e a integração com uma API real seguem
  pendentes.

## Carregamento da aba Tarefas

- A listagem por casa passou a buscar atribuições e reclamações em lotes no
  Supabase. A contagem e o voto do usuário consideram o ciclo atual de cada
  tarefa.
- Em uma medição de leitura com o Supabase configurado, a casa com 142
  tarefas retornou a lista completa em 3,63 s e o filtro de sete dias em
  1,64 s. Na lista completa, foram duas leituras para atribuições e duas
  para reclamações. A medição simulou a sincronização de estados em memória.
- A suíte do backend sem os arquivos de integração passou com 758 testes.
  O Ruff passou nos arquivos Python alterados.

## ECH-368 · Roleta por ocorrência de rodízio

- O administrador habilita `usar_roleta: true` no `POST /rotatividades/`. A
  criação exige pelo menos dois participantes com vínculo ativo na casa. O
  padrão é `false`, inclusive para os rodízios já cadastrados.
- A ocorrência é gerada no calendário do rodízio. O giro abre à meia-noite no
  fuso cadastrado ou no instante da criação, se a primeira ocorrência cair
  no próprio dia. A janela fecha após 24 horas corridas. Podem girar e ser
  sorteados os participantes cadastrados que ainda tenham vínculo ativo.
- `GET /tarefas/{id}/roleta` devolve os candidatos, a permissão de giro, os
  horários e o estado (`agendada`, `aberta`, `expirada`, `atribuindo` ou
  `atribuida`). `POST /tarefas/{id}/roleta` recebe apenas o ID na URL e
  devolve o mesmo contrato com o resultado. Reenvios de participantes ativos
  recebem o resultado persistido. A resposta de tarefa traz o resumo em
  `roleta`, e o `PATCH` genérico protege a atribuição e o vencimento.
- Giro e job usam a mesma atualização condicional por ocorrência. Se a
  gravação parar depois da escolha, o próximo processamento usa o mesmo
  responsável para completar a atribuição. O job diário busca roletas
  vencidas mesmo fora do horizonte de geração e reaproveita o balanceamento
  por pontuação potencial acumulada. Uma pausa interrompe novas gerações,
  enquanto as ocorrências existentes seguem suas janelas.
- O vencimento é o maior entre o original e 24 horas após a atribuição
  confirmada. Antes disso, a tarefa fica sem conclusão, aviso de vencimento
  ou atraso. A saída do responsável é bloqueada enquanto a ocorrência
  estiver aberta. Se todos os participantes saírem antes da escolha, as
  ocorrências existentes são preservadas e o job registra a pendência.

### Publicação e validação

- Aplicar [40.sql](../../docs/migrations/40.sql) antes de publicar o backend.
  A integração da tela com as novas rotas fica na entrega de frontend. O
  giro fecha pelo relógio do backend, e o balanceamento ocorre na execução
  seguinte do job diário.
- A partir de `src/backend`, passaram 833 testes unitários e 31 testes de
  integração de rodízios, tarefas, vínculos e casas em PostgreSQL 18.7 e
  PostgREST 16.6 locais e descartáveis. Foram exercitados giros concorrentes,
  disputa com o job, recuperação de atribuição e saída durante a gravação.
- A aplicação das migrations 01 a 40 preservou um rodízio e sua atribuição
  registrados antes da migration 40. O Ruff passou nos arquivos Python
  alterados. A execução do cron em produção segue sem verificação.

## ECH-370 · Primeiro nome na roleta

- A roda compartilhada usa fatias coloridas da paleta Caldera, aro escuro e
  ponteiro laranja. Os rótulos e o resultado exibem o primeiro nome,
  com o resultado em destaque direto sobre a superfície da tela.
  A legenda mantém a ordem das fatias em telas estreitas, com nomes
  longos ou com mais de oito candidatos. Para primeiros nomes iguais, exibe
  o nome completo. Com movimento reduzido, o resultado aparece sem giro.
- Os dois formulários de criação de rodízio oferecem a opção de roleta.
  Na edição do rodízio, o modo de atribuição é informativo. Nas ocorrências
  com roleta, a edição administrativa oferece nome, descrição, peso e
  tolerância de atraso.
- Os detalhes consultam a janela, a permissão e os candidatos no
  backend. A tela consulta novamente na abertura, no fechamento e ao
  retornar à aba. Durante o envio, o botão fica indisponível. Se a resposta
  do giro falhar, a tela verifica o estado antes de liberar outra tentativa.
  Após a atribuição, a tarefa é recarregada para atualizar o responsável e
  o vencimento.

### Validação do frontend

- A partir de `src/frontend`, passaram os 196 testes do `npm test`,
  a checagem TypeScript e o ESLint dos arquivos alterados. O lint geral
  apontou finais de linha mistos já presentes em
  `src/hooks/use-color-scheme.web.ts`.
- O Expo exportou Web e Android. No Chrome com API simulada, foram
  verificados os nomes, a posição final do ponteiro, a tela estreita,
  o movimento reduzido e o giro com um candidato. Também foram conferidos
  a abertura e o fechamento da janela, a permissão de giro, o clique
  duplo, o resultado por balanceamento, a recuperação após erro e o envio
  de `usar_roleta` pelos dois formulários de criação.
- A interação em um dispositivo Android e a validação contra a API
  publicada seguem pendentes.
