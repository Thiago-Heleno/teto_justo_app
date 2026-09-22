# Pendências de integração da criação de tarefas — Sprint 2

Referência: regras do frontend e código local conferidos em 22/09/2026.

## Limite da entrega

A criação continua sendo uma demonstração em memória, sem chamadas à API
ou gravação. A lista possui seus próprios exemplos e ainda não recebe as
tarefas criadas. O fluxo futuro será frontend → API FastAPI → Supabase;
credenciais privilegiadas do banco não devem estar no aplicativo.

## Regras atuais e diferenças de contrato

| Informação | Frontend de criação | Backend/banco local e próximo ajuste |
| --- | --- | --- |
| Nome e descrição | Nome obrigatório após remover espaços; descrição opcional. | Validar nome não vazio também no servidor. |
| Peso | Apenas 1, 2 ou 3, como dificuldade. | `TarefaCriar` e `TarefaAtualizar` ainda aceitam 4; o serviço grava `peso` em `tarefa.dificuldade`. Restringir criação, edição e constraint a 1..3, com tratamento acordado para registros antigos de peso 4. |
| Responsável | Exatamente um ID em `usuarios_atribuidos: [string]`. | A API e a tabela `atribuida` ainda permitem vários. Exigir exatamente um na criação e na troca de responsável; impedir múltiplas atribuições por tarefa no banco. |
| Prazo | `prazo_dias` inteiro de 1 a 5. Não calcula uma data nesta demonstração. | A API exige `data_fim` futuro. Alinhar recebimento dos dias e cálculo no servidor, usando um instante de criação confiável e regras de fuso. |
| Pontuação | Não existe campo nem conversão de peso em pontos. | A API exige `pontuacao` em 10, 20, 30 ou 40. Peso e pontuação são independentes no contrato atual; definir origem/valor da pontuação sem ampliar o formulário automaticamente. |
| Atraso máximo | Não existe campo no formulário. | A API exige `atraso_maximo > 0`, que representa tolerância após o vencimento. Não confundir esse campo com o novo prazo de execução de até 5 dias. |
| Casa e usuário | Casa e moradores fictícios. | Obter UUIDs reais, casa atual e sessão. Alinhar `fk_usuario_id` e, se representar o criador, derivá-lo da sessão no servidor. |
| Estado | A criação só exibe confirmação local. | Alinhar criação no estado `pendente`; a API também aceita `atrasada`, `finalizado` e `nao_feito`. |

Enviar o objeto local diretamente ainda não funciona: faltam campos exigidos,
os IDs são fictícios e `prazo_dias` não faz parte do schema. O schema atual
rejeita campos extras. O peso já é persistido pelo backend; a antiga pendência
de incluir esse campo na API foi superada.

## Backend e banco

- [ ] Aplicar as três regras novas também na criação e edição do servidor:
  um responsável, peso 1..3 e prazo inteiro de 1..5 dias. Rejeitar zero,
  negativos, frações e valores acima do limite.
- [ ] Definir quando começa a contagem e se cada dia representa 24 horas ou
  um dia de calendário; calcular e retornar `data_fim` com fuso explícito.
  Definir se uma futura edição conserva o início original ou reinicia o prazo.
- [ ] Planejar migration para unicidade de tarefa em `atribuida`, tratando
  previamente tarefas com múltiplos responsáveis. Uma constraint de unicidade
  impede dois vínculos; criação transacional deve garantir que exista um.
- [ ] Revisar crédito de pontos e histórico de tarefas já compartilhadas:
  o trigger ainda percorre todos os responsáveis. Não escolher automaticamente
  quem receberá pontos de registros antigos.
- [ ] Restringir `dificuldade` a três níveis no banco e alinhar valores antigos,
  testes e respostas. Não reduzir os níveis de `pontuacao` por inferência.
- [ ] Definir pontuação e atraso máximo aplicáveis ao fluxo de criação. O
  limite de 5 dias solicitado é prazo para fazer a tarefa, não penalidade.
- [ ] Preservar a verificação de vínculo com a casa já existente no serviço.
  Tornar gravação de tarefa e atribuição atômica: hoje são operações separadas.
- [ ] Conferir migrations efetivamente aplicadas no ambiente de testes,
  incluindo as de pontuação e atraso. Arquivos versionados não comprovam
  configuração do Supabase real; não reaplicar migrations indiscriminadamente.
- [ ] Conferir fuso, permissões/RLS e regras de crédito único na conclusão,
  inclusive alterações de responsável e requisições concorrentes.

## Autenticação e acesso antes de usar dados reais

- [ ] Implementar login com verificação de senha, credencial gerada no
  servidor, consulta do usuário atual e logout com revogação.
- [ ] Fechar/substituir o CRUD público de sessões; o código local ainda
  permite criar/listar sessões sem autenticação. Ver [autenticacao.md](autenticacao.md).
- [ ] Disponibilizar casas acessíveis e moradores por casa com IDs e nomes.
- [ ] Restringir leituras e alterações ao acesso por recurso. Preservar a
  autorização de criação pelo proprietário da casa já presente no servidor.

## Frontend na integração

- [ ] Substituir casa/moradores fictícios por dados do usuário autenticado.
  Tratar carregamento, erro, lista vazia e perda de acesso.
- [ ] Configurar URL da API por ambiente e CORS para web. No celular,
  `localhost` aponta para o celular. O `main.py` atual não configura CORS.
- [ ] Adaptar o modelo local ao contrato acordado e confirmar apenas após
  `201`, com resumo baseado na resposta do servidor.
- [ ] Bloquear envios simultâneos e preservar valores em erros de validação,
  sessão, permissão ou conexão. Não repetir automaticamente uma criação
  cujo resultado ficou incerto.
- [ ] Atualizar a lista após a criação confirmada. Manter filtros de prazo
  baseados no vencimento retornado pelo backend.
- [ ] Manter campos e opções fáceis de rever; edição de tarefas existentes
  não faz parte da entrega desta tela.

## Critérios para concluir a integração

- [ ] Criar com pesos 1, 2 e 3, prazos de 1 e 5 dias e um responsável;
  consultar novamente e conferir persistência.
- [ ] Rejeitar nenhum/dois responsáveis, membro de outra casa, nome vazio,
  peso 4, prazo zero, fracionário ou maior que 5.
- [ ] Confirmar troca de responsável sem vínculo duplicado, gravação sem
  registros parciais e crédito único para quem concluiu.
- [ ] Testar autorização e sessões ausentes, inválidas, expiradas e revogadas.
- [ ] Validar vencimento em fusos diferentes e transições de calendário.
- [ ] Verificar Android, iOS e web. Testes com banco falso não substituem
  integração em Supabase exclusivo para testes.

## Validação desta revisão

Conferência estática de `schemas/tarefa.py`, `routers/tarefa.py`,
`services/tarefa.py`, `routers/sessao.py`, `main.py` e documentação/migrations
de pontuação e atraso. Nenhum código backend foi alterado, nenhuma migration
foi aplicada e nenhum banco real foi acessado.
