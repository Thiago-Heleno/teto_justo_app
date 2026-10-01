BEGIN;

-- Rodada de conclusão da tarefa: começa em 0 e aumenta a cada reabertura.
ALTER TABLE tarefa
    ADD COLUMN reaberturas INT NOT NULL DEFAULT 0 CHECK (reaberturas >= 0);

-- Rodada a que cada evento pertence. Eventos já gravados ficam na rodada 0.
ALTER TABLE score_event
    ADD COLUMN ciclo INT NOT NULL DEFAULT 0 CHECK (ciclo >= 0);

-- Um crédito e um estorno por usuário, tarefa e rodada.
DROP INDEX uq_score_event_credito;

CREATE UNIQUE INDEX uq_score_event_credito
    ON score_event (fk_usuario_id, fk_tarefa_id, ciclo) WHERE tipo = 'credito';

CREATE UNIQUE INDEX uq_score_event_reversal
    ON score_event (fk_usuario_id, fk_tarefa_id, ciclo) WHERE tipo = 'reversal';

COMMIT;
