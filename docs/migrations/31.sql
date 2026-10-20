BEGIN;

ALTER TABLE tarefa ADD COLUMN aviso_inicio_tentado_em TIMESTAMPTZ;

CREATE INDEX idx_tarefa_aviso_inicio
    ON tarefa (data_inicio, id)
    WHERE estado_atual = 'pendente' AND aviso_inicio_tentado_em IS NULL;

COMMIT;
