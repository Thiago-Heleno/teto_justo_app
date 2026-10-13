# Perfil do usuário (editar dados e excluir conta)

## Objetivo

Tela de perfil após o login para editar nome e e-mail (`PATCH /usuarios/{id}`) e excluir a conta (`DELETE /usuarios/{id}`) com confirmação.

## Decisão: proprietário de casa

A exclusão é **bloqueada** com `409` e a mensagem "Você é proprietário de uma casa e não pode excluir a conta. Exclua a casa antes de excluir a conta." Não existe transferência de propriedade, então o proprietário precisa excluir a casa antes (`DELETE /casas/{id}`).

## Alterações

- `services/usuario.py`: bloqueio do proprietário; contas sem histórico são apagadas de verdade; contas com histórico (erro de FK `23503`) são anonimizadas (ver abaixo); o PATCH recusa e-mail de outra conta (`400`), porque a tabela `usuario` não tem UNIQUE em `email` e o login exige e-mail único.
- Frontend: `components/perfil.tsx` (tela), `services/perfil-api.ts`, `app/(app)/perfil.tsx` (aba "Perfil" em `app-tabs.tsx` e `app-tabs.web.tsx`) e botão "Meu perfil" em `selecao-casa.tsx`, para quem ainda não tem casa. `utils/cadastro.ts` ganhou `validarPerfil`, reutilizada por `validarCadastro`.
- A edição atualiza a tela com a resposta do PATCH; o token não muda, então não há novo login. A exclusão só encerra a sessão local depois do `204` e o app volta ao login.
- O logout já existia na Home e na seleção de casa e não foi duplicado.

## Exclusão de contas com histórico: anonimização (sem migration)

As FKs de `pertencer`, `atribuida`, `score_event`, `tarefa` e `rotatividade` para `usuario` são `RESTRICT` (migrations 01, 07 e 18), então quem já teve casa, tarefa ou pontos não pode ser apagado. Nesse caso o backend anonimiza a conta, na ordem:

1. `409` se houver tarefa `pendente` ou `atrasada` atribuída ao usuário (nada é alterado).
2. Sai de todas as casas ativas (`ServicoPertencer.deletar_pertencer`, mesmas regras da saída voluntária).
3. Apaga as sessões.
4. Troca nome por "Usuário removido", e-mail por `removido-<id>@example.com`, e zera telefone, foto e `senha_hash` (o login recusa conta sem hash).

Pontos e eventos continuam no histórico das casas, atribuídos a "Usuário removido". O proprietário continua bloqueado com `409`.

Riscos: a sequência não é transacional (várias chamadas ao Supabase). Se o update final falhar, o usuário já saiu das casas e perdeu as sessões, mas pode entrar de novo e repetir a exclusão. Saída e anonimização exigem que `telefone`, `foto` e `senha_hash` aceitem NULL; isso vem das migrations lidas, não foi conferido no banco.

## Validações executadas

- Backend: `pytest` nos testes `*unitario*` (todos os coletados passaram, incluindo os 13 de usuário) e `ruff check` nos arquivos alterados. Sete arquivos não foram coletados porque o Python local não tem o pacote `redis`; eles não foram executados. Os testes de usuário usam banco falso em memória e `MagicMock`; não houve teste contra o Supabase.
- Frontend: `npm run test:tarefas` (47 testes, passaram; 3 novos cobrem edição, exclusão e 409 do proprietário). A UI não foi aberta em dispositivo nem no navegador.
- `tsc` aponta rotas tipadas desatualizadas (`/pontuacao`, `/perfil`) em `app-tabs.web.tsx`, que o Expo regenera ao iniciar.
