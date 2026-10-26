BEGIN;

ALTER TABLE tarefa
ADD COLUMN aviso_atraso_enviado_em TIMESTAMPTZ;

CREATE INDEX idx_tarefa_aviso_atraso
    ON tarefa (data_fim, id)
    WHERE estado_atual IN ('pendente', 'atrasada')
      AND aviso_atraso_enviado_em IS NULL;

COMMIT;
