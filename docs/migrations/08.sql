BEGIN;

-- Converte os codigos legados de estado para os valores textuais do quadro.
ALTER TABLE tarefa
    ALTER COLUMN estado_atual TYPE VARCHAR(10)
    USING CASE estado_atual
        WHEN 0 THEN 'pendente'
        WHEN 1 THEN 'atrasada'
        WHEN 2 THEN 'finalizado'
        WHEN 3 THEN 'nao_feito'
        ELSE estado_atual::TEXT
    END;

ALTER TABLE tarefa
    ADD CONSTRAINT CK_Tarefa_estado_atual
    CHECK (estado_atual IN ('pendente', 'atrasada', 'finalizado', 'nao_feito'));

-- Atende a busca do quadro de tarefas filtrada por casa e estado.
CREATE INDEX IDX_Tarefa_Casa_Estado
    ON tarefa (fk_casa_id, estado_atual);

COMMIT;
