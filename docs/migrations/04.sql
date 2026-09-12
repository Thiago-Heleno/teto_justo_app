-- Define a data de criação no próprio PostgreSQL para novos registros.
-- CURRENT_TIMESTAMP é calculado no início da transação que executa o INSERT.

BEGIN;

ALTER TABLE public.usuario
    ALTER COLUMN data_criacao SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE public.tarefa
    ALTER COLUMN criado_em SET DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE public.sessao
    ALTER COLUMN criado_em SET DEFAULT CURRENT_TIMESTAMP;

COMMIT;
