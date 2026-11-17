# ECH-337 · Roleta de responsáveis

A criação e a edição de tarefas avulsas oferecem atribuição manual ou por
sorteio ao administrador da casa. A edição permite sorteio em tarefas pendentes
ou atrasadas.

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
