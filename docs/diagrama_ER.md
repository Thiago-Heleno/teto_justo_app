# ER atualizado — Teto Justo

Fonte: branch `main` de [Thiago-Heleno/teto_justo_app](https://github.com/Thiago-Heleno/teto_justo_app), commit `6d51bf69cf11b0fde8a4f3aafa3dc6cf5299e23b`. Referência visual e formato: `docs/diagrama_ER.png` e `docs/diagrama_ER.brM3`. Modelo atualizado com `docs/migrations/01.sql` a `26.sql` e os schemas e serviços do backend.

Arquivos: `diagrama_ER.png` (imagem) e `diagrama_ER.brM3` (editável no BR Modelo). O arquivo nativo foi gravado e desserializado com as classes do BR Modelo 3.31. A imagem foi renderizada pelo próprio motor do BR Modelo. Não foi consultado nem alterado o banco em produção; este diagrama representa o código versionado.

## Representação conceitual

Retângulos representam entidades; losangos, relacionamentos; círculos, atributos; círculos preenchidos, identificadores. Cardinalidades junto a uma entidade indicam quantas vezes uma instância dessa entidade participa do relacionamento. `dias_semana` é multivalorado.

| Elemento no ER | Persistência |
| --- | --- |
| Usuario, Casa, Sessao, Tarefa | Tabelas de mesmo nome |
| Rotatividade | `rotatividade` |
| Score_event | `score_event` |
| Pertencer, atributo score | `pertencer`, chave composta `(fk_usuario_id, fk_casa_id)` |
| Atribuida | `atribuida`, chave composta `(fk_usuario_id, fk_tarefa_id)` |
| Participa, atributo ordem | `rotatividade_participante`, chave composta `(fk_rotatividade_id, fk_usuario_id)` |
| Administra | `casa.fk_usuario_id` |
| Cria tarefa | `tarefa.fk_usuario_id` |
| Contem | `tarefa.fk_casa_id` |
| Cria rodizio / Configura | `rotatividade.fk_usuario_id` / `rotatividade.fk_casa_id` |
| Gera ocorrencia | `tarefa.rotatividade_id` |
| Ativa | `sessao.fk_usuario_id` |
| Recebe / Registra / Origina | FKs de usuário, casa e tarefa em `score_event` |

As FKs são representadas pelas ligações, sem duplicá-las como atributos no modelo conceitual. Identificadores das entidades são UUID. `usuario_tipo` permanece como atributo armazenado; a especialização antiga Admin/Comum foi substituída pela relação Administra, porque `services/autorizacao.py` verifica o proprietário de cada casa, e não um tipo global de usuário.

## Regras relevantes

- Cada tarefa possui um responsável no fluxo atual do backend. A tabela `atribuida` ainda permite múltiplos responsáveis por tarefa; a cardinalidade `(1,1)` representa a regra atual da API, não uma restrição UNIQUE no banco.
- Cada rodízio possui ao menos dois participantes distintos da casa. O BR Modelo usa `(1,n)` em Participa; o mínimo de dois é explicitado na legenda. `ordem` é positiva e única dentro de cada rodízio.
- O proprietário é vinculado como morador na criação da casa. Por isso Casa participa de Pertencer com `(1,n)` no modelo de negócio. Um usuário pode estar cadastrado sem casa, sessão, tarefa, rodízio ou evento.
- Uma tarefa pode estar vinculada a zero ou uma rotatividade; uma rotatividade pode gerar várias tarefas. A ocorrência é única por `(rotatividade_id, ocorrencia_em)`.
- `dificuldade` é o peso (1, 2 ou 3); `pontuacao` é derivada desse peso (10, 25 ou 50). `tipo_de_penalidade` foi removido pela migration 11 e não aparece no ER.
- `reaberturas` identifica a rodada da tarefa. `score_event.ciclo` identifica a rodada do evento; `tipo` permite `credito` e `reversal`. As migrations 24 e 26 permitem no máximo um crédito e um estorno por usuário, tarefa e ciclo. Assim uma tarefa pode originar vários eventos ao longo das reaberturas.
- `pertencer.score` é o saldo materializado; `score_event` registra o histórico. Cada evento referencia um usuário, uma casa e uma tarefa. Não foi inventada uma FK direta de evento para Pertencer: ela não existe nas migrations.
- `token` mantém o nome da coluna de Sessao; o serviço armazena um hash SHA-256, e não o token em texto puro.

As cardinalidades usam as regras do backend. Algumas FKs legadas em Casa, Sessao e Tarefa ainda aceitam NULL nas migrations; isso não é apresentado como obrigatoriedade física no banco. `proxima_ocorrencia` permanece no ER porque a coluna ainda existe. Campos calculados da API, como `data_fixa`, `estrategia_penalidade` e `resultado_pontuacao`, não foram tratados como novas colunas.

## Validação

Revisadas as 26 migrations e as regras de autorização, tarefas, sessões, casas e rotatividade do backend. Conferidos os atributos persistidos e o mapeamento das nove tabelas. Verificado o ciclo de gravação e leitura do `.brM3` e revisada visualmente a imagem exportada.
