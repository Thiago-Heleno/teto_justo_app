-- Adiciona atraso maximo permitido para conclusao da tarefa.

BEGIN;

ALTER TABLE tarefa
    ADD COLUMN atraso_maximo INT;

COMMIT;