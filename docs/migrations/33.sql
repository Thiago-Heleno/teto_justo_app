BEGIN;

ALTER TABLE casa
    ADD COLUMN politica_reclamacao TEXT NOT NULL DEFAULT 'nenhuma'
    CONSTRAINT ck_casa_politica_reclamacao
    CHECK (politica_reclamacao IN ('nenhuma', 'uma_reclamacao', 'votacao'));

CREATE TABLE reclamacao_tarefa (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_tarefa_id UUID NOT NULL REFERENCES tarefa (id) ON DELETE CASCADE,
    fk_usuario_id UUID NOT NULL REFERENCES usuario (id) ON DELETE RESTRICT,
    ciclo INT NOT NULL,
    descricao TEXT CHECK (descricao IS NULL OR length(descricao) <= 500),
    criada_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_reclamacao_tarefa UNIQUE (fk_tarefa_id, fk_usuario_id, ciclo)
);

COMMIT;
