BEGIN;

ALTER TABLE tarefa DROP CONSTRAINT CK_Tarefa_prazo_calculado;
ALTER TABLE tarefa ADD CONSTRAINT CK_Tarefa_prazo_calculado CHECK (
    prazo_dias IS NULL OR (
        data_inicio IS NOT NULL AND data_fim IS NOT NULL
        AND data_fim > data_inicio
    )
);

COMMIT;
