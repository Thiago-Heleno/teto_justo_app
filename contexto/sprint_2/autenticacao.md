# Autenticação por sessão — Sprint 2

## Objetivo

Disponibilizar o usuário autenticado nas rotas protegidas a partir de um token
Bearer associado a uma sessão válida. Requisições sem credencial, com token
desconhecido ou com sessão expirada recebem `401 Unauthorized`.

## Implementação

- `core/autenticacao.py` define o esquema `HTTPBearer`, a dependência
  `obter_usuario_atual` e o tipo reutilizável `UsuarioAtual`.
- `services/sessao.py` consulta a sessão pelo token, valida `expira_em` e busca
  somente os campos públicos do usuário vinculado.
- Todos os erros de credencial usam a mesma mensagem e o cabeçalho
  `WWW-Authenticate: Bearer`.
- Falhas de infraestrutura ou erros inesperados da aplicação não são
  convertidos em erro de credencial.
- As rotas de Casa, Tarefa e Pertencer foram protegidas. Em Usuário, somente o
  cadastro continua público; listagem, consulta, atualização e exclusão exigem
  autenticação.
- A criação de casa usa o usuário autenticado como proprietário; o cliente não
  pode escolher `fk_usuario_id` no corpo da requisição.
- `/health` permanece público.
- O workflow do backend passou a executar os testes unitários de autenticação.

Não foi adicionada biblioteca JWT. A implementação reutiliza o token opaco e a
tabela `sessao` já existentes no projeto.

## Autorização de administrador por casa

- O administrador de uma casa é o usuário registrado em
  `casa.fk_usuario_id`. O campo global `usuario.usuario_tipo` não participa
  dessa decisão.
- Criar, atualizar ou excluir uma tarefa exige que o usuário do token seja o
  administrador da casa correspondente. Um usuário autenticado que não seja o
  proprietário recebe `403 Forbidden` sem que a mutação seja executada.
- Na atualização e exclusão, a casa usada na autorização vem da tarefa já
  persistida. `fk_casa_id` não é aceito no PATCH, evitando mover a tarefa para
  contornar a autorização.
- Atualizar ou excluir a própria casa também exige o proprietário. Isso impede
  que a exclusão em cascata da casa seja usada para apagar tarefas sem passar
  pela autorização de administrador.
- Token ausente, inválido ou expirado continua sendo falha de autenticação e
  retorna `401`; token válido sem permissão é falha de autorização e retorna
  `403`.
- Nenhuma migration foi alterada ou criada: a implementação reutiliza a relação
  de proprietário que já existe na tabela `casa`.

## Testes e validações

- `75` testes unitários aprovados, incluindo ausência de credencial, esquema
  incorreto, token inexistente, expirado, duplicado, sessão órfã, autenticação
  válida, autorização do proprietário e bloqueio de criação, atualização e
  exclusão por moradores.
- Compilação dos módulos de backend concluída sem erro.
- Análises estáticas completas do backend aprovadas com Ruff e Bandit.
- Coleta completa dos testes concluída: `85` casos encontrados.
- OpenAPI conferido: as rotas protegidas exibem o esquema Bearer; `/health` e
  `POST /usuarios/` não exigem autenticação.
- Os testes de integração foram atualizados para usar o mesmo usuário como
  portador do token e proprietário da casa, além de cobrir o `403` para um
  morador. Eles não foram executados localmente porque dependem do Supabase de
  teste configurado por secrets no GitHub Actions.

## Limitações e pendências

- Ainda não existe uma rota de login que valide a senha e gere o token no
  servidor.
- O CRUD público atual de Sessão permite criar sessões para um usuário
  arbitrário e expõe tokens. Ele precisa ser substituído por login/logout antes
  de esta autenticação ser considerada segura para produção.
- Os tokens continuam armazenados em texto puro e não possuem restrição de
  unicidade no banco. O hardening recomendado é armazenar apenas o hash e criar
  uma constraint única.
- `expira_em` é `TIMESTAMP` sem fuso. Valores sem offset são tratados como UTC;
  uma migration futura deve considerar `TIMESTAMPTZ`.
- A leitura de casas e tarefas continua permitida a qualquer usuário
  autenticado e não é filtrada por vínculo de moradia. As rotas de Pertencer e
  as demais operações de usuário também ainda não possuem autorização por
  recurso.
- O modelo atual admite um único administrador por casa. Suporte a múltiplos
  administradores exigirá modelagem adicional em uma migration futura.
- Casas legadas com `fk_usuario_id` nulo não possuem administrador e tarefas
  legadas sem `fk_casa_id` não permitem identificar a casa da autorização.
  Esses registros ficam bloqueados para mutações e precisam de auditoria e
  backfill antes de uma migration futura tornar as relações obrigatórias.
