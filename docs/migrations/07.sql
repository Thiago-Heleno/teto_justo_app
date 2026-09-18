BEGIN;

ALTER TABLE tarefa
    ADD COLUMN dificuldade INT,
    ADD COLUMN tipo_de_penalidade INT,
    ADD COLUMN concluida_em TIMESTAMP;

ALTER TABLE tarefa
    ADD CONSTRAINT CK_Tarefa_dificuldade CHECK (dificuldade IN (1, 2, 3, 4));

ALTER TABLE tarefa
    ADD CONSTRAINT CK_Tarefa_tipo_de_penalidade CHECK (tipo_de_penalidade IN (1, 2, 3, 4));

ALTER TABLE tarefa
    ADD CONSTRAINT CK_Tarefa_pontuacao CHECK (pontuacao IN (10, 20, 30, 40));

CREATE TABLE score_event (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_Usuario_id UUID NOT NULL,
    fk_Casa_id UUID NOT NULL,
    fk_Tarefa_id UUID NOT NULL,
    pontuacao INT NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT UQ_ScoreEvent_Usuario_Tarefa UNIQUE (fk_Usuario_id, fk_Tarefa_id)
);

ALTER TABLE score_event ADD CONSTRAINT FK_ScoreEvent_Usuario
    FOREIGN KEY (fk_Usuario_id)
    REFERENCES Usuario (id)
    ON DELETE RESTRICT;

ALTER TABLE score_event ADD CONSTRAINT FK_ScoreEvent_Casa
    FOREIGN KEY (fk_Casa_id)
    REFERENCES Casa (id)
    ON DELETE CASCADE;

ALTER TABLE score_event ADD CONSTRAINT FK_ScoreEvent_Tarefa
    FOREIGN KEY (fk_Tarefa_id)
    REFERENCES Tarefa (id)
    ON DELETE CASCADE;

COMMIT;
