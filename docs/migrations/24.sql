BEGIN;

ALTER TABLE score_event ADD COLUMN tipo TEXT NOT NULL DEFAULT 'credito' CHECK (tipo IN ('credito', 'reversal'));
ALTER TABLE score_event DROP CONSTRAINT UQ_ScoreEvent_Usuario_Tarefa;
CREATE UNIQUE INDEX uq_score_event_credito ON score_event (fk_usuario_id, fk_tarefa_id) WHERE tipo = 'credito';

COMMIT;