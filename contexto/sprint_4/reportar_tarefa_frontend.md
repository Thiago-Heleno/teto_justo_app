# Reportar tarefa no detalhe e no extrato

O morador pode denunciar uma conclusão no detalhe da tarefa ou em **Pontuação → Movimentações recentes**. As duas telas usam `src/frontend/src/components/botao-reportar-tarefa.tsx`. O botão aparece para os demais moradores ativos quando a política da casa permite denúncias. O prazo inclui o instante exato de 24 horas após a conclusão. A tela oculta o botão quando esse prazo termina.

## Decisões

- O extrato devolve a política atual da casa e o instante de conclusão apenas no crédito do ciclo que continua finalizado. O serviço aproveita as consultas existentes à casa e às tarefas. Estornos e créditos de ciclos anteriores continuam abrindo o detalhe.
- As duas telas enviam o instante de conclusão recebido da API no parâmetro opcional `concluida_em` de `POST /tarefas/{id}/reclamacoes`. O backend valida o prazo e rejeita com HTTP 409 uma denúncia destinada a uma execução anterior. Clientes que omitem o parâmetro continuam usando o contrato anterior.
- Após o envio, o botão indica “Reportado”. Se a votação reabrir a tarefa pelo extrato, a aba recarrega o placar e as movimentações para mostrar o estorno. O registro da denúncia, a votação e o estorno usam os serviços existentes.

- O botão das duas telas exibe os votos registrados no ciclo atual sobre o número de moradores ativos que podem votar. O responsável fica fora do denominador. O detalhe usa a contagem da tarefa e o extrato busca os votos das tarefas da página em lote. Ao enviar, o app usa a contagem confirmada pela API.

## Retirada e estado do voto — 2026-11-11

- `src/backend/services/reclamacao.py` compartilha as validações entre envio e retirada. `DELETE /tarefas/{id}/reclamacoes?concluida_em=...` remove somente o voto do usuário autenticado na tarefa e no ciclo atual. Repetir a retirada não afeta outros votos; o usuário pode votar novamente.
- A retirada exige morador ativo, usuário diferente do responsável, política habilitada e tarefa ainda finalizada dentro das 24 horas inclusivas. Conclusão antiga retorna 409. Não desfaz uma reabertura já realizada, não estorna pontos nem agenda notificação.
- `services/tarefa.py`, `services/placar.py`, os routers e os schemas de tarefa e extrato devolvem `usuario_reclamou`. O estado considera o usuário autenticado, não o morador filtrado no extrato. O extrato reutiliza sua consulta de votos em lote; não há alteração de banco ou migration.
- `botao-reportar-tarefa.tsx` recebe o estado persistido nas duas telas. Fica clicável após votar, informa seleção e ação para acessibilidade e bloqueia cliques repetidos durante a requisição. `tarefas-api.ts` envia a retirada; `pontuacao.tsx` atualiza contagem e seleção com a resposta. A navegação entre abas já recarrega os dados ao receber foco.

## Validação local desta alteração

- A partir de `src/frontend`, `npm run test:tarefas`: **99 testes aprovados**, incluindo envio HTTP da retirada e quatro testes do componente compartilhado. Estes renderizam com React e componentes nativos simulados: verificam os dois estados visuais, ação de envio/retirada, resposta confirmada e bloqueio de clique duplicado. Não substituem validação visual do app completo.
- A partir de `src/backend`, os testes de `test_reclamacao_unitario.py` e `test_servico_placar_unitario.py`, excluindo os casos de rota (`-k "not rota"`), aprovaram **71 casos**, com Supabase em memória e somente os imports do SDK Firebase simulados no processo. Os 13 novos casos de serviço falharam antes da implementação e passaram depois.
- Os **118 testes** de `test_servico_tarefa_unitario.py` também passaram com a mesma simulação dos imports Firebase.
- Ruff passou nos arquivos Python alterados. Prettier passou nos arquivos frontend alterados.
- A execução direta do pytest ficou bloqueada pela ausência de `firebase-admin`. O teste HTTP novo com TestClient ficou sem concluir e foi interrompido; os casos HTTP permanecem pendentes neste ambiente. Não foi executada a suíte completa nem validação com banco real.
- ESLint dos arquivos frontend alterados ficou bloqueado por `lucide-react-native` ausente. TypeScript ficou bloqueado por esse pacote e pelos imports de `firebase/app` e `firebase/messaging`. A validação visual nas duas telas do aplicativo permanece pendente.

## Permissão de report do administrador — 2026-11-16

### Problema e decisão

O detalhe da tarefa e o extrato de pontuação exigiam que o usuário aparecesse
na lista de moradores ativos para mostrar o botão de report. O serviço de
reclamações aplicava a mesma restrição a `pertencer`. Isso impedia o proprietário
da casa quando o seu vínculo não aparecia como ativo, embora o acesso à casa
já reconheça o proprietário pelo campo `casa.fk_usuario_id`.

O proprietário pode reportar uma tarefa de outro responsável mesmo sem registro
ativo em `pertencer`. O responsável atribuído à execução continua impedido de
reportar, inclusive quando é o próprio proprietário. Os demais usuários ainda
precisam ter vínculo ativo; tarefa finalizada, janela inclusiva de 24 horas,
política habilitada e validação do ciclo continuam obrigatórias.

### Alterações

- `src/backend/services/reclamacao.py`: inclui `casa.fk_usuario_id` entre os
  participantes autorizados ao registrar ou retirar um report, sem dispensar a
  exclusão do responsável.
- `src/backend/services/tarefa.py`: considera o proprietário na contagem de
  votantes elegíveis e no limite de reabertura, sem duplicá-lo se já houver
  vínculo ativo.
- `src/frontend/src/utils/pode-reportar-tarefa.ts`: centraliza a identificação
  do morador ou administrador elegível e a contagem de votantes únicos.
- `src/frontend/src/components/detalhe-tarefa.tsx` e
  `src/frontend/src/app/(app)/tarefas.tsx`: mostram o report ao proprietário
  mesmo quando não aparece na lista de moradores.
- `src/frontend/src/app/(app)/pontuacao.tsx`: usa o proprietário da casa ativa
  para a mesma regra no extrato e para exibir os votos possíveis.
- `src/backend/tests/test_reclamacao_unitario.py`: cobre proprietário com
  vínculo ausente ou inativo, retirada de report, proprietário responsável
  bloqueado e cálculo do limite de votação.
- `src/backend/tests/test_ciclo_vida_tarefa_unitario.py`: completa o registro
  simulado de casa com seu identificador obrigatório de proprietário.
- `src/frontend/scripts/pode-reportar-tarefa.test.mjs`: cobre elegibilidade do
  proprietário, ex-morador e responsável, e total de votantes sem duplicação.

### Validações executadas

- **287 testes de backend aprovados** em sete módulos de testes associados a
  reclamações, tarefas, ciclo de vida, placar, visibilidade e contratos HTTP,
  usando Supabase em memória e um bootstrap local para simular imports de SDKs
  externos indisponíveis neste ambiente.
- **8 testes de elegibilidade frontend aprovados** com Node.js e suporte
  experimental de remoção de tipos TypeScript.
- **4 arquivos frontend analisados sem erros de sintaxe** com parser TypeScript.
- Compilação de bytecode Python dos serviços e testes alterados aprovada.

### Limitações

Não houve teste com banco real nem execução visual no aplicativo. A instalação
das dependências Python do backend não estava disponível neste ambiente, de
modo que os testes foram executados com substituições locais de imports do
Supabase/PostgREST, Firebase e bibliotecas de autenticação; não substituem uma
execução do projeto com dependências instaladas. Não foi executado TypeScript
`tsc` completo ou lint completo do frontend porque suas dependências locais
não estavam presentes. Não há migração de banco.
