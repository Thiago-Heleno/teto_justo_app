# Verificação de e-mail no cadastro — Sprint 4

## Objetivo e comportamento

Ao tocar em **Criar conta**, o app valida o formulário, o backend envia por
e-mail (via `ServicoEmail`, ver `resend_email.md`) um código aleatório de 5
dígitos e o app abre a tela **Confirme seu e-mail**. A conta só é criada depois
que o código é digitado corretamente.

- Código: 5 dígitos numéricos, gerado com `secrets`, sem zero à esquerda
  (10000–99999). Vale 10 minutos.
- `POST /usuarios/codigo-verificacao` (público): recebe `nome`, `email` e
  `senha`, valida os dados, recusa e-mail já cadastrado (400), envia o e-mail e
  devolve `{token_verificacao, expira_em}`.
- `POST /usuarios/` (público): passou a exigir `codigo` (5 dígitos) e
  `token_verificacao`. Código errado, de outro e-mail ou expirado devolve
  400 `Código inválido ou expirado.` e nenhum usuário é criado.
- Tela de código: teclado numérico, `autoComplete="one-time-code"`, **Reenviar
  código** (espera de 30 s) e **Corrigir meus dados**, que volta ao cadastro.
  Depois da verificação o app volta ao login com a mensagem de conta criada.
- Limites: 5 envios por e-mail e 20 por IP, e 5 tentativas de código por
  e-mail e 20 por IP, a cada 15 minutos. Ao estourar, 429 com `Retry-After`.
- E-mail: HTML simples com estilos inline, usando as cores do `DESIGN.md`
  (fundo Pumice, cartão Limestone com raio 40 px, marca em Ember, código em
  Obsidian sobre bloco Sulfur, sem sombras) e fontes com fallback seguro para
  clientes de e-mail (DM Sans → Arial; título e código em Impact/Arial Narrow).
  Sem imagens.

## Arquivos e decisões

Backend (`src/backend`):

- `services/verificacao_email.py`: `ServicoVerificacaoEmail` (`emitir`,
  `verificar`, `montar_html`).
- `routers/usuario.py`: nova rota e verificação em `POST /usuarios/`.
- `schemas/usuario.py`: `UsuarioCadastro` e `VerificacaoEmailResposta`.
- `services/usuario.py`: checagem de e-mail duplicado extraída para
  `garantir_email_disponivel` (mesma mensagem e status).
- `services/limite_login.py`: `LimitadorLogin` aceita mensagem própria;
  `get_limitador_verificacao` cria a instância desta feature.
- Testes: `tests/test_verificacao_email_unitario.py`,
  `tests/test_usuarios_verificacao_unitario.py`; fixture `com_verificacao` em
  `tests/conftest.py`, usada pelos testes de integração que criam usuário.

Frontend (`src/frontend`):

- `src/components/verificacao-email.tsx`: nova tela.
- `src/app/login.tsx`: estado `pendente` que alterna cadastro, verificação e
  login (sem rota nova).
- `src/components/cadastro.tsx`, `src/services/autenticacao-api.ts`,
  `src/utils/cadastro.ts`: pedido do código, novo corpo de `cadastrar` e
  filtro de dígitos. `scripts/autenticacao-api.test.mjs` foi atualizado.

Decisões:

- **Sem estado e sem banco.** O token é `{exp}.{HMAC-SHA256}` sobre
  `e-mail normalizado|exp|código`. O código nunca é armazenado; quem tem o
  token não consegue deduzi-lo sem a chave. Não há tabela nem migration.
- **Chave:** subchave derivada de `CASA_CONVITE_SECRET`, sem variável nova.
  Sem essa variável (mínimo de 32 bytes), as rotas respondem 503.
- **Código sem padrão "memorável":** 5 dígitos aleatórios; filtrar sequências
  reduziria as 90 mil combinações.
- Os dados do cadastro (incluindo a senha) ficam só em memória no app até a
  confirmação e são descartados ao concluir ou voltar.
- Falha no envio do e-mail devolve 503 e não consome tentativa de envio.

## Validação executada

Comandos executados a partir de `src/backend`:

- `python -m pytest tests -k unitario`: 443 aprovados, 31 não selecionados
  (integração com banco). Os novos cobrem: 5 dígitos sem zero à esquerda,
  expiração em 10 minutos, código errado, e-mail diferente, token adulterado e
  malformado, segredo ausente, HTML com o código e as cores, e-mail duplicado,
  falha no envio, limites de envio e de tentativas (429) e criação da conta
  apenas com o código correto. Banco, e-mail e relógio são simulados.
- `python -m ruff check services routers schemas tests`: aprovado.

A partir de `src/frontend`:

- `node --experimental-test-module-mocks --test scripts/autenticacao-api.test.mjs`
  e `npm run test:tarefas`: 58 aprovados.
- `npx prettier --end-of-line auto --check` nos arquivos alterados: aprovado.
- `npx tsc --noEmit`: nenhum erro nos arquivos alterados; o comando falha por
  erros de rotas tipadas (`/calendario`, `/gerenciar-casa` etc.) que já existiam
  nos outros arquivos de `src/app`.
- `npx eslint` aponta apenas diferenças de fim de linha (CRLF) neste checkout,
  inclusive em arquivos não alterados; o arquivo novo, em LF, passa limpo.

## Limites

- Não executei os testes de integração com banco real; apenas adaptei as
  fixtures que criam usuário para enviar código e token.
- Não executei o fluxo completo no app, nem enviei o e-mail real desta feature;
  o layout do e-mail não foi visto em um cliente de e-mail.
- Sem estado, o código **não é de uso único** e pedir outro não invalida o
  anterior: qualquer código emitido para o e-mail vale até expirar. A conta só
  pode ser criada uma vez (e-mail duplicado dá 400).
- Os limites ficam na memória de cada processo, como no login; em várias
  instâncias serverless eles enfraquecem. O IP vem de `request.client.host`,
  que atrás de proxy pode ser o do proxy (mesmo comportamento do login).
- Enquanto o Resend não tiver domínio verificado, o remetente padrão só entrega
  para o e-mail da conta Resend; outros usuários não receberão o código.
- A troca de e-mail em `PATCH /usuarios/{id}` continua sem verificação.
- Ao voltar da tela do código, nome e senha precisam ser digitados de novo.
- Não há login automático após a verificação.
