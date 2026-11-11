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
