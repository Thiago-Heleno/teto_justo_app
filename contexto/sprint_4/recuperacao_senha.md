# Recuperação de senha — Sprint 4

## Objetivo e comportamento

Permitir que quem esqueceu a senha crie outra usando um código enviado por
e-mail (via `ServicoEmail`, ver `resend_email.md`). Backend e telas do app.

Fluxo no app: **Esqueci minha senha** (login) → tela com o e-mail → tela com
código, nova senha e confirmação → volta ao login com a mensagem "Senha alterada.
Entre com a nova senha." A resposta de `recuperar-senha` é igual exista a conta
ou não, então a tela do código diz "Se ... estiver cadastrado".

- `POST /usuarios/recuperar-senha` (público): recebe `{email}`, devolve
  `{token_verificacao, expira_em}`. Responde igual exista a conta ou não; o
  e-mail com o código só é enviado se a conta existir e tiver senha.
- `POST /usuarios/redefinir-senha` (público): recebe `email`, `codigo` (5
  dígitos), `token_verificacao` e `nova_senha`. Em caso de sucesso responde 204,
  troca `senha_hash` e apaga todas as sessões da conta. Código errado, expirado,
  já usado, de outro fluxo, de conta inexistente ou removida: 400
  `Código inválido ou expirado.`
- Limites: 5 pedidos por e-mail e 20 por IP, e 5 tentativas de código por
  e-mail e 20 por IP, a cada 15 minutos (429 com `Retry-After`). Usa um
  limitador próprio (`get_limitador_recuperacao`), separado do cadastro.

## Arquivos e decisões

Backend (`src/backend`):

- `services/verificacao_email.py`: `emitir` e `verificar` ganharam `proposito`
  (padrão `"cadastro"`) e `vinculo` (padrão vazio), ambos assinados no HMAC;
  `montar_html` aceita título e texto.
- `services/usuario.py`: `obter_hash_senha`, `redefinir_senha` e `_hash_senha`
  (extraído de `criar_usuario`).
- `routers/usuario.py`, `schemas/usuario.py`, `services/limite_login.py`: rotas,
  `RecuperarSenhaEntrada`, `RedefinirSenhaEntrada` e o limitador.
- Testes: `tests/test_recuperacao_senha_unitario.py` e novos casos em
  `tests/test_verificacao_email_unitario.py`.

Frontend (`src/frontend`):

- `src/components/recuperar-senha.tsx` e `src/components/redefinir-senha.tsx`:
  as duas telas (esta com campo de código, **Reenviar código** após 30 s e voltar).
- `src/app/login.tsx`: estado `recuperacao` (sem token pede o e-mail; com token
  pede o código), sem rota nova. `src/components/login.tsx`: botão
  **Esqueci minha senha**; a mensagem de sucesso reaproveita `mensagemCadastro`.
- `src/services/autenticacao-api.ts`: `solicitarRecuperacaoSenha` e
  `redefinirSenha`. `src/utils/cadastro.ts`: `validarEmail` e `validarNovaSenha`
  (extraídas de `validarPerfil`/`validarCadastro`, sem mudar o comportamento).
  `src/utils/recuperacao-senha.ts`: mensagens de erro comuns às duas telas.
- Testes: casos novos em `scripts/autenticacao-api.test.mjs`.

Decisões:

- **Propósito no HMAC:** um código de cadastro não redefine senha e vice-versa.
- **Uso único sem tabela:** o `vinculo` da redefinição é o `senha_hash` atual.
  Ao trocar a senha o hash muda e o código deixa de validar. O update é
  condicional (`senha_hash` igual ao que validou o código), então dois pedidos
  simultâneos com o mesmo código não passam ambos.
- **Sem enumeração de contas:** o token é emitido sempre; conta inexistente ou
  removida (`senha_hash` nulo) recebe a mesma resposta, sem e-mail. Na redefinição
  esses casos caem no mesmo 400 e contam como falha no limitador.
- **Sessões encerradas** após a troca, para derrubar logins de quem tenha
  invadido a conta.

## Validação executada

Comandos executados a partir de `src/backend`:

- `python -m pytest tests -k unitario`: todos aprovados (31 testes de integração
  com banco não selecionados). Banco, e-mail e relógio são simulados.
- `python -m ruff check services routers schemas tests`: aprovado.

A partir de `src/frontend`:

- `node --experimental-test-module-mocks --test scripts/autenticacao-api.test.mjs`:
  27 aprovados.
- `npm run test:tarefas`: 63 aprovados e 1 falha em `scripts/notificacoes.test.mjs`
  (`expo-notifications` não instalado neste checkout); a falha já existia
  (58 aprovados e 1 falha sem estas mudanças).
- `npx prettier --end-of-line auto --check` nos arquivos alterados: aprovado.
- `npx tsc --noEmit`: nenhum erro nos arquivos alterados.
- `npx eslint`: só diferenças de fim de linha (CRLF) nos arquivos que já
  existiam; os arquivos novos, em LF, passam limpos.

## Limites

- O fluxo não foi executado contra Supabase real nem com envio real pelo Resend;
  o comportamento de `.eq("senha_hash", ...)` no update vem de um banco falso.
- Pedir um novo código não invalida o anterior: qualquer código emitido vale até
  expirar ou até a senha mudar.
- Quando a conta existe a resposta demora mais (espera o Resend); quem medir o
  tempo consegue distinguir os casos.
- Os limites ficam na memória do processo, como no login e no cadastro.
- Enquanto o Resend não tiver domínio verificado, só o e-mail da conta Resend
  recebe o código.
- As telas não foram abertas no app nem testadas em dispositivo ou emulador, e
  não há teste de componente: os testes do frontend cobrem as chamadas à API, as
  validações e as mensagens de erro.
