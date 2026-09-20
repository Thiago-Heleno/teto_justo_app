# Pendências de integração da criação de tarefas — Sprint 2

Referência: código local revisado em 20/09/2026.

## Objetivo e limite da entrega

Registrar o trabalho futuro para conectar a tela de criação ao backend FastAPI
e à persistência no Supabase. A tarefa atual continua sendo somente o frontend
com dados simulados, descrito em [frontend_tarefas.md](frontend_tarefas.md).
Esta lista não representa implementação concluída nem amplia a entrega atual.
Os campos e regras podem ser revistos antes da integração.

O fluxo previsto é **frontend → API FastAPI → Supabase**. O aplicativo não
deve receber credenciais de acesso privilegiado ao banco.

## O que já existe

- Formulário com nome, descrição opcional, peso, prazo e seleção de um ou
  mais responsáveis; confirmação apenas local, sem persistência.
- `POST /tarefas/` com retorno `201`, consulta por ID e consulta por casa.
- Validação de sessão Bearer e autorização de criação pelo proprietário
  da casa (`casa.fk_usuario_id`), independentemente de `usuario_tipo`.
- Gravação de tarefas em `tarefa` e de responsáveis em `atribuida`.
- Migrations versionadas para dificuldade, pontuação, estados textuais e
  crédito de pontos. Sua aplicação no Supabase real não foi verificada.

## Contrato a alinhar

| Informação | Situação atual | Pendência |
| --- | --- | --- |
| Nome e descrição | A tela e a API possuem `nome` e `descricao`. | Validar nome não vazio também no backend; manter descrição opcional. |
| Peso | A tela usa `peso` com níveis `1..4`, provisoriamente como dificuldade. A migration `07.sql` define `dificuldade` (`1..4`) e `pontuacao` (`10`, `20`, `30`, `40`), mas os schemas de tarefa não expõem esses campos. | Confirmar significado e nome no contrato; incluir o campo acordado na criação, resposta e persistência. Não presumir conversão automática de peso em pontos. |
| Prazo | A tela converte data e hora locais para ISO; a API recebe `data_fim`. A migration original usa `TIMESTAMP`. | Definir o tratamento de fuso no banco e validar prazo futuro também no servidor, preservando o instante na leitura. |
| Responsáveis | A API recebe `usuarios_atribuidos` com UUIDs; a tela usa IDs fictícios. | Carregar moradores reais e exigir no backend pelo menos um responsável, todos vinculados à casa. |
| Casa | A API exige `fk_casa_id`; a tela usa uma casa fictícia fixa. | Obter a casa selecionada no fluxo da aplicação e verificar acesso. |
| Usuário vinculado | A API de tarefa ainda exige `fk_usuario_id` no corpo, separado dos responsáveis. | Definir se representa o criador. Se for, derivá-lo do usuário autenticado no servidor e ajustar o contrato. |
| Estado | A API exige `estado_atual`: `pendente`, `atrasada`, `finalizado` ou `nao_feito`. | Alinhar criação inicial como `pendente`; não reutilizar os antigos códigos numéricos. |

**Atenção:** enviar apenas o objeto local da tela não atende ao contrato atual:
faltam casa, usuário vinculado e estado, e os responsáveis não têm UUIDs reais.
Além disso, `peso` não é persistido: `TarefaCriar` não declara esse campo e
atualmente ignora campos extras. O envio pode aparentar sucesso sem salvar o peso
se os demais campos forem válidos.

## Pendências do backend e banco

### Autenticação e acesso

- [ ] Implementar login com verificação de senha e geração de credencial no
  servidor, consulta do usuário autenticado e logout com revogação da sessão.
- [ ] Fechar/substituir o CRUD público de sessões, que hoje permite criar
  sessões de terceiros e expõe tokens. É um bloqueio para integrar com dados
  reais; detalhes em [autenticacao.md](autenticacao.md).
- [ ] Disponibilizar consulta das casas acessíveis ao usuário e dos moradores
  da casa selecionada, com IDs e nomes. A listagem atual de `pertencer` é global
  e não fornece diretamente esse resultado.
- [ ] Restringir leituras por vínculo de moradia e proteger alterações de
  usuários, vínculos e pontuações por recurso. Ter um token válido não deve
  permitir alterar dados de qualquer pessoa.
- [ ] Preservar a autorização de administrador no servidor, mesmo quando a
  interface ocultar a ação de criar para outros moradores.

### Persistência e consistência

- [ ] Conferir as migrations aplicadas no ambiente de testes, incluindo UUIDs,
  atribuições e as migrations `06.sql` a `09.sql`. Aplicar somente as pendentes
  no ambiente confirmado; não reaplicar arquivos indiscriminadamente.
- [ ] Implementar o contrato de peso acordado e definir a origem da pontuação.
  O trigger de finalização usa `tarefa.pontuacao`; se ela estiver nula e houver
  responsáveis, a inserção em `score_event.pontuacao NOT NULL` pode falhar.
  Confirmar esse cenário no banco de testes. Não é necessário criar uma tela
  de conclusão para resolver o contrato de criação.
- [ ] Definir valores/defaults para os demais campos que não estão no formulário
  (`tipo_de_penalidade`, `atraso_maximo`), conforme a regra do produto, sem
  acrescentar novos campos visuais automaticamente.
- [ ] Validar vínculo dos responsáveis com a casa e impedir gravação parcial:
  hoje a tarefa é inserida antes das atribuições, em operações separadas.
  Uma falha nas atribuições não deve deixar uma tarefa incompleta salva.
- [ ] Definir tratamento de fuso de `data_fim` e das sessões, com migration
  se necessária, e revisar dados legados sem proprietário ou casa.
- [ ] Conferir permissões/RLS e a credencial usada pelo backend no ambiente
  real; a presença dos arquivos de migration não comprova a configuração
  efetiva do Supabase.

## Pendências do frontend

- [ ] Receber usuário autenticado, sessão e casa selecionada do fluxo geral
  do aplicativo; substituir os dados de demonstração por dados da API.
- [ ] Configurar o endereço da API por ambiente. Em um celular físico,
  `localhost` aponta para o próprio celular, não para o computador do backend.
  Para a versão web, configurar CORS para as origens usadas; não há esse
  middleware no `main.py` atual.
- [ ] Carregar moradores com estados de carregamento, erro e lista vazia;
  impedir envio sem casa válida ou sem responsáveis disponíveis.
- [ ] Enviar `POST /tarefas/` com a sessão e o contrato acordado. Mostrar
  confirmação apenas após `201`, usando os dados retornados pelo servidor.
- [ ] Bloquear envios simultâneos e preservar o formulário em caso de falha.
  Tratar `401` (sessão), `403` (permissão), `422` (validação), indisponibilidade
  e falhas do servidor. Não reenviar automaticamente uma criação cujo resultado
  ficou incerto após interrupção da conexão.
- [ ] Manter os campos fáceis de alterar. Edição de tarefas já existentes é
  uma funcionalidade futura, não um requisito desta integração de criação.

## Ordem sugerida e critérios de conclusão

1. Alinhar peso, usuário vinculado, estado inicial e tratamento de prazo.
2. Resolver autenticação, permissões e consulta de casas/moradores.
3. Adequar contrato e persistência no backend/banco de testes.
4. Conectar a tela e validar o fluxo completo.

- [ ] Administrador faz login, escolhe a casa e cria tarefa com um responsável
  e com vários; uma nova consulta confirma nome, descrição, peso, prazo e vínculos.
- [ ] Morador sem permissão recebe `403`; sessão ausente, inválida, expirada ou
  revogada recebe `401`. Rotas públicas não permitem obter/forjar sessão alheia.
- [ ] Backend rejeita nome em branco, peso fora do contrato, prazo inválido,
  lista vazia de responsáveis e usuários que não pertencem à casa.
- [ ] Falha na gravação dos responsáveis não deixa tarefa parcial; problemas
  de conexão não produzem confirmação falsa nem reenvio automático duplicado.
- [ ] Prazo mantém o mesmo instante ao salvar e consultar em fusos diferentes.
- [ ] Validar em Android e iOS, além de uma conferência web. Testes com banco
  falso devem ser identificados como tal; persistência real deve ser validada
  em um Supabase exclusivo para testes, com limpeza dos registros temporários.

## Validação deste documento

Conferência estática dos schemas, rotas, serviço de tarefa, formulário e
migrations versionadas. Nenhuma integração foi implementada, nenhuma migration
foi aplicada e nenhum banco real foi acessado nesta sessão documental.
