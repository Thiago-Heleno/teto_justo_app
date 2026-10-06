-- Aplicar uma vez, depois de auditar a tabela sessao e confirmar a migration 27.
-- Tokens legados em texto puro já não autenticam na API; removê-los encerra o passivo.
-- Se um hash estiver duplicado, ambas as sessões são revogadas, sem escolher um usuário.
BEGIN;

DELETE FROM public.sessao
WHERE token IS NULL
   OR token !~ '^sha256:[0-9a-f]{64}$'
   OR expira_em IS NULL
   OR expira_em <= (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

DELETE FROM public.sessao
WHERE token IN (
    SELECT token FROM public.sessao GROUP BY token HAVING COUNT(*) > 1
);

ALTER TABLE public.sessao ALTER COLUMN token SET NOT NULL;
ALTER TABLE public.sessao ADD CONSTRAINT uq_sessao_token UNIQUE (token);

COMMIT;
