# ECH-334 — Formatação de datas e fallback de fuso

- Os campos de vencimento na criação e na edição de tarefas aplicam a máscara `dd-mm-AAAA` e validam a data civil. A API recebe `AAAA-MM-DD`. A edição omite `data_fixa` do PATCH quando o dia fica igual.
- O backend usa UTC quando o fuso da casa está ausente ou é inválido. Para interpretar ou recalcular dias fixos, o fuso válido da tarefa tem precedência. Na sequência, são usados o da casa e UTC. O padrão de criação de casas continua sendo `America/Sao_Paulo` e as regras de rodízio existentes mantêm o fuso salvo.
- Lista e detalhe mostram prazos por intervalo no mesmo fuso da casa usado pelo calendário. O job de avisos contabiliza falhas de consulta do fuso e deixa o aviso disponível para nova tentativa.

## Validação

- Backend com dados simulados. A suíte unitária do CI passou com 721 testes. O Ruff passou.
- Frontend. `npm run test:tarefas` passou com 93 testes. O TypeScript passou com `tsc --noEmit`.
- O ESLint passou em uma cópia com finais de linha LF, como no CI. A execução no checkout Windows foi interrompida após essa verificação.
- No Chrome com API simulada, foram verificados digitação, colagem, exclusão, rejeição de data inválida, payloads de criação e edição e exibição no fuso da casa. A exportação do Expo gerou os bundles web, Android e iOS. A interação nativa em dispositivo ou emulador ficou pendente.
