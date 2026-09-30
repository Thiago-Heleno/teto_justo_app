# Autenticação por sessão — Sprint 2

## Objetivo

Disponibilizar o usuário autenticado nas rotas protegidas a partir de um token
Bearer associado a uma sessão válida. Requisições sem credencial, com token
desconhecido ou com sessão expirada recebem `401 Unauthorized`.

## Implementação

- `core/autenticacao.py` define o esquema `HTTPBearer`, a dependência
  `obter_usuario_atual` e o tipo reutilizável `UsuarioAtual`.
- `services/sessao.py` consulta a sessão pelo hash do token, valida `expira_em` e busca
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

## Login, logout e aplicativo

- `POST /sessoes/login` recebe JSON com `email` e `senha`. Valida a senha
  com bcrypt e responde `200` com `token` e `expira_em`. A resposta usa
  `Cache-Control: no-store`. Credenciais incorretas recebem a mesma mensagem
  `401`, sem indicar se a conta existe.
- O servidor gera um token opaco com 32 bytes aleatórios e validade de 24 horas.
  O banco recebe apenas SHA-256 com prefixo `sha256:`, reutilizando a coluna
  `sessao.token`. Não foi criada migration nem função no banco.
- Tokens legados em texto puro e o próprio hash armazenado não são aceitos como
  Bearer. Todos os clientes precisam fazer login novamente.
- `POST /sessoes/logout` exige Bearer e retorna `204`, revogando somente o
  token apresentado, vinculado ao usuário autenticado. Outras sessões continuam
  funcionando.
- O CRUD de `/sessoes/` e `/sessoes/{id}` foi removido das rotas, schemas e
  serviços. Não há endpoint para listar tokens ou escolher o usuário da sessão.
- O frontend mostra o formulário de login antes de montar as abas, inclusive
  quando uma rota protegida é aberta diretamente. A tela inicial autenticada
  oferece acesso às tarefas e logout; o formulário antigo que imprimia a senha
  no console foi retirado.
- `sessao-store.ts` usa Zustand e o armazenamento existente:
  SecureStore no celular e `localStorage` na web. A sessão salva é validada em
  `GET /usuarios/eu` ao abrir o app. Respostas `401` removem a sessão atual;
  uma resposta atrasada de uma sessão anterior não apaga um login novo.
- `api.ts` centraliza as requisições autenticadas; `autenticacao-api.ts`
  implementa login/logout. `tarefas-api.ts` usa essa sessão em execução, sem
  ler `EXPO_PUBLIC_TETO_JUSTO_TOKEN`. Login não depende do ID de uma casa.

## Pertencer

As rotas já estavam implementadas em `src/backend/routers/pertencer.py` e
registradas em `main.py`. A conferência do OpenAPI confirma:

| Método | Rota | Acesso |
| --- | --- | --- |
| POST | `/pertencer/` | Administrador da casa |
| GET | `/pertencer/` | Autenticado |
| GET | `/pertencer/{fk_usuario_id}/{fk_casa_id}` | Autenticado |
| DELETE | `/pertencer/{fk_usuario_id}/{fk_casa_id}` | Administrador da casa |

Não há PATCH público de score: a pontuação é alterada pelos serviços próprios.

## Testes e validações

- Backend: 297 testes unitários aprovados, com dependências de banco simuladas.
  Cobrem senha inválida, login, hash persistido, expiração, rejeição de tokens
  legados, logout, preservação de outra sessão e ausência do CRUD antigo.
- Frontend: 36 testes aprovados com `npm run test:tarefas`, incluindo
  autenticação, restauração, erro de rede, expiração, logout sem corpo,
  armazenamento indisponível e rejeição do token de build.
- Ruff e Bandit aprovados no backend; ESLint aprovado nos arquivos de frontend
  alterados. O lint geral, excluindo artefatos gerados, encontrou 4.473 problemas
  de formatação em arquivos não alterados, principalmente finais de linha CRLF.
  Eles não foram reformatados nesta tarefa.
- TypeScript aprovado após regenerar o cache local de rotas do Expo. Coleta
  completa do backend concluída com 320 casos; os 23 testes de integração
  não foram executados.
- Build web de produção gerado em pasta temporária com configuração fictícia.
  O JavaScript exportado não contém referência à variável de token de build.
- Teste de navegador em 1280×900 e 390×844, usando API simulada: acesso direto
  protegido, senha incorreta, login, restauração após recarregar, logout e
  expiração aprovados, sem erros de JavaScript. Capturas visuais conferidas.
- A integração real de login/logout com Supabase foi atualizada, mas não
  executada: depende de um banco isolado de teste.

## Limitações e pendências antes de distribuição pública

- Falta limitar tentativas de login na infraestrutura ou no backend.
- Ainda não há restrição única para o hash na tabela de sessões; a autenticação
  rejeita resultados duplicados. Sessões legadas devem ser auditadas e removidas
  antes da publicação; nenhuma limpeza foi executada no banco nesta tarefa.
- O cadastro real está na API; a interface atual fornece login/logout, sem
  recuperação de senha ou tela de cadastro.
- O frontend ainda usa `EXPO_PUBLIC_CASA_ID` para selecionar a casa; não há
  seletor de moradia por usuário.
- Na web, `localStorage` continua acessível a scripts da página. Uma sessão
  web por cookie `HttpOnly` e proteção CSRF requer uma implementação específica.
- `expira_em` usa `TIMESTAMP` sem fuso, interpretado como UTC. Uma migration
  futura deve considerar `TIMESTAMPTZ`.
- Listagem e consulta gerais de casas, tarefas e vínculos ainda não filtram por
  moradia. Operações de usuário ainda precisam de autorização por recurso.
  Moradores e consultas de pontuação já verificam acesso à casa.
- O modelo admite um administrador por casa. Casas legadas sem proprietário e
  tarefas sem casa continuam bloqueadas para mutações até saneamento dos dados.
- O armazenamento nativo precisa de validação em dispositivo; nenhum APK ou IPA
  foi gerado ou publicado nesta tarefa.
