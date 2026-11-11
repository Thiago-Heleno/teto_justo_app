# Reportar tarefa no detalhe e no extrato

O morador pode denunciar uma conclusão no detalhe da tarefa ou em **Pontuação → Movimentações recentes**. As duas telas usam `src/frontend/src/components/botao-reportar-tarefa.tsx`. O botão aparece para os demais moradores ativos quando a política da casa permite denúncias. O prazo inclui o instante exato de 24 horas após a conclusão. A tela oculta o botão quando esse prazo termina.

## Decisões

- O extrato devolve a política atual da casa e o instante de conclusão apenas no crédito do ciclo que continua finalizado. O serviço aproveita as consultas existentes à casa e às tarefas. Estornos e créditos de ciclos anteriores continuam abrindo o detalhe.
- As duas telas enviam o instante de conclusão recebido da API no parâmetro opcional `concluida_em` de `POST /tarefas/{id}/reclamacoes`. O backend valida o prazo e rejeita com HTTP 409 uma denúncia destinada a uma execução anterior. Clientes que omitem o parâmetro continuam usando o contrato anterior.
- Após o envio, o botão indica “Reportado”. Se a votação reabrir a tarefa pelo extrato, a aba recarrega o placar e as movimentações para mostrar o estorno. O registro da denúncia, a votação e o estorno usam os serviços existentes.

- O botão das duas telas exibe os votos registrados no ciclo atual sobre o número de moradores ativos que podem votar. O responsável fica fora do denominador. O detalhe usa a contagem da tarefa e o extrato busca os votos das tarefas da página em lote. Ao enviar, o app usa a contagem confirmada pela API.

## Validação local

- Para o contador, passaram os 20 testes do serviço de placar em `src/backend` e os 94 testes de tarefas em `src/frontend`. Uma renderização isolada do botão com componentes nativos simulados verificou `0/2`, `1/2`, `2/2`, o rótulo acessível e a ocultação por prazo e responsável.

- A partir de `src/frontend`, `npm run test:tarefas` aprovou 94 testes.
- A partir de `src/backend`, `python -m pytest -q tests/test_servico_placar_unitario.py` aprovou 19 testes. Outros 38 testes do serviço de reclamação passaram com o import do SDK Firebase simulado. Os testes cobrem a expiração, a identificação do ciclo e a rejeição de uma conclusão desatualizada.
- O ambiente local estava sem `firebase-admin`, `firebase` e `lucide-react-native`. A suíte completa do backend, o ESLint e o TypeScript ficaram bloqueados. O TestClient também ficou bloqueado ao iniciar o loop de eventos do Windows. A interface não foi validada visualmente.
