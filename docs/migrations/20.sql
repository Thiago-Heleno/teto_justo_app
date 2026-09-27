BEGIN;

-- 14.sql pode recriar esta função legada em bancos que já receberam 15.sql.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'tarefa'
            AND column_name = 'prazo_dias'
    ) THEN
        RAISE EXCEPTION 'Aplique 14.sql antes de 20.sql.';
    END IF;
    IF to_regprocedure(
        'public.registrar_conclusao_tarefa(uuid,uuid,integer,timestamptz,integer,integer,timestamp,timestamp,uuid)'
    ) IS NULL THEN
        RAISE EXCEPTION 'Aplique 15.sql antes de 20.sql.';
    END IF;
END;
$$;

DROP TRIGGER IF EXISTS TRG_Tarefa_Finalizada_Credita_Pontos ON public.tarefa;
DROP FUNCTION IF EXISTS public.fn_tarefa_finalizada_credita_pontos();

COMMIT;
