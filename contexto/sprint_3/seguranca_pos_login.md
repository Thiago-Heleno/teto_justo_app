# Segurança após o login — ECH-205 (Sprint 3)

## Comportamento

- O login usa Redis compartilhado para contar falhas por e-mail normalizado e
  pelo IP da conexão. As chaves contêm somente hashes; cinco falhas por e-mail
  ou vinte por IP em quinze minutos bloqueiam novas tentativas com `429` e
  `Retry-After`. A tentativa é reservada atomicamente antes de conferir a senha,
  evitando que chamadas simultâneas ultrapassem o limite. Uma autenticação
  bem-sucedida limpa as falhas daquele e-mail e retira a própria reserva do IP,
  preservando as falhas dos demais. Redis indisponível resulta em `503`, sem token.
- Cada login válido emite um token opaco aleatório e armazena seu SHA-256. A
  restrição única em `sessao.token` não limita o número de dispositivos do
  mesmo usuário. Tokens legados em texto puro continuam inválidos.
- Leituras de casas, tarefas e vínculos exigem propriedade da casa ou vínculo
  ativo. Listas são filtradas antes da paginação; consultas de tarefa por ID
  verificam acesso antes de montar a resposta. Perfis são visíveis somente ao
  próprio usuário e a moradores de casas compartilhadas. Atualização e
  exclusão de conta exigem o próprio usuário.
- O app mostra o tempo de espera informado por `Retry-After`. O cadastro no
  aplicativo permanece como tarefa separada.

## Implantação

1. Confirme que `docs/migrations/27.sql` já foi aplicada ao Supabase de destino,
   pois as verificações de moradia usam `pertencer.ativo`.
2. Configure `REDIS_URL` em todas as instâncias do backend e confirme a
   conectividade. Se houver proxy, configure no Uvicorn somente os IPs de
   proxies confiáveis; nunca confie em `X-Forwarded-For` enviado diretamente
   pelo cliente.
3. Antes da migration 28, audite a tabela em um banco de teste e depois no
   ambiente de destino. Registre somente contagens, sem exportar tokens:

   ```sql
   SELECT
     COUNT(*) FILTER (WHERE token IS NULL OR token !~ '^sha256:[0-9a-f]{64}$')
       AS legadas,
     COUNT(*) FILTER (WHERE expira_em IS NULL OR
       expira_em <= (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')) AS expiradas,
     COUNT(*) FILTER (WHERE token IN (
       SELECT token FROM public.sessao WHERE token IS NOT NULL
       GROUP BY token HAVING COUNT(*) > 1
     )) AS duplicadas
   FROM public.sessao;
   ```

4. Aplique `docs/migrations/28.sql` em banco de teste e confira que sessões
   legadas, expiradas e hashes duplicados foram revogados. Faça login com dois
   dispositivos e confirme tokens distintos e logout independente. Em seguida,
   aplique a migration ao ambiente de destino em janela controlada. A alteração
   da restrição única bloqueia escritas na tabela durante a execução.
5. Implante backend e frontend e valide `401`, `403`, `429`, `503`, `Retry-After`
   e a visibilidade entre duas casas reais antes de qualquer distribuição
   pública. Tokens revogados exigem novo login no aplicativo.

## Verificação local

A suíte do backend sem integração passou com 343 testes; Ruff e Bandit passaram. Os testes
unitários exercitam limites, expiração, Redis indisponível, paginação e acesso
entre casas. TypeScript e 64 testes do frontend passaram. Os dois arquivos
TypeScript alterados passaram no ESLint com a regra de fim de linha ajustada
ao checkout Windows; o lint global falhou em milhares de erros CRLF preexistentes
da `main`. A migration 28 passou pelo parser PostgreSQL e foi executada em
PostgreSQL descartável (PGlite) com sessões legadas,
expiradas e duplicadas: a limpeza, `UNIQUE`, `NOT NULL` e duas sessões do mesmo
usuário passaram. O teste de integração do limitador passou com Redis 7 local.
Os testes de integração com o Supabase de teste não foram executados, pois este
checkout não possui suas credenciais nem confirmação da migration 28 aplicada.
