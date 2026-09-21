BEGIN;

-- tipo_de_penalidade foi substituido pela taxa de desconto baseada em
-- atraso_maximo (ver docs/migrations/10.sql). A coluna nunca foi exposta
-- pela API e deixou de ser lida pelo trigger de credito de pontos.
ALTER TABLE tarefa
    DROP CONSTRAINT IF EXISTS CK_Tarefa_tipo_de_penalidade;

ALTER TABLE tarefa
    DROP COLUMN IF EXISTS tipo_de_penalidade;

COMMIT;
