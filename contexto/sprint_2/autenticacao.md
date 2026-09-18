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
- `/health` permanece público.
- O workflow do backend passou a executar os testes unitários de autenticação.

Não foi adicionada biblioteca JWT. A implementação reutiliza o token opaco e a
tabela `sessao` já existentes no projeto.

## Testes e validações

- `63` testes unitários aprovados, incluindo ausência de credencial, esquema
  incorreto, token inexistente, expirado, duplicado, sessão órfã, autenticação
  válida e propagação de erro de banco.
- Compilação dos módulos de backend concluída sem erro.
- Coleta completa dos testes concluída: `72` casos encontrados.
- OpenAPI conferido: as rotas protegidas exibem o esquema Bearer; `/health` e
  `POST /usuarios/` não exigem autenticação.
- Os testes de integração foram atualizados para criar uma sessão temporária e
  enviar o header Bearer, mas não foram executados localmente porque dependem do
  Supabase de teste configurado por secrets no GitHub Actions.

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
- Autenticação identifica o usuário, mas ainda não verifica se ele pode acessar
  determinada casa, tarefa ou vínculo. A autorização por recurso permanece uma
  tarefa separada.
