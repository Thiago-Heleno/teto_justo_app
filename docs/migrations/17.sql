BEGIN;

ALTER TABLE tarefa
    ADD COLUMN tipo VARCHAR(8),
    ADD COLUMN modo_prazo VARCHAR(9);

ALTER TABLE tarefa
    ADD CONSTRAINT CK_Tarefa_tipo
    CHECK (tipo IN ('rotativa', 'unitaria'));

ALTER TABLE tarefa
    ADD CONSTRAINT CK_Tarefa_modo_prazo
    CHECK (modo_prazo IN ('dia_fixo', 'intervalo'));

COMMIT;
