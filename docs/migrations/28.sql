BEGIN;

DELETE FROM sessao
WHERE token IS NULL
   OR token !~ '^sha256:[0-9a-f]{64}$'
   OR expira_em IS NULL
   OR expira_em <= (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

DELETE FROM sessao
WHERE token IN (
    SELECT token FROM sessao GROUP BY token HAVING COUNT(*) > 1
);

ALTER TABLE sessao ALTER COLUMN token SET NOT NULL;
ALTER TABLE sessao ADD CONSTRAINT uq_sessao_token UNIQUE (token);

COMMIT;
