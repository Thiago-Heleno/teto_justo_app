BEGIN;

ALTER TABLE rotatividade ADD COLUMN usar_roleta BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE pertencer ADD CONSTRAINT uq_pertencer_vinculo_ativo
    UNIQUE (fk_usuario_id, fk_casa_id, ativo);

ALTER TABLE tarefa
    ADD COLUMN roleta_expira_em TIMESTAMPTZ,
    ADD COLUMN roleta_responsavel_id UUID,
    ADD COLUMN roleta_decidida_em TIMESTAMPTZ,
    ADD COLUMN roleta_origem TEXT,
    ADD COLUMN roleta_atribuida_em TIMESTAMPTZ,
    ADD COLUMN roleta_vinculo_ativo BOOLEAN GENERATED ALWAYS AS (
        CASE WHEN roleta_responsavel_id IS NOT NULL
            AND estado_atual IN ('pendente', 'atrasada') THEN TRUE END
    ) STORED,
    ADD CONSTRAINT fk_tarefa_roleta_vinculo FOREIGN KEY (
        roleta_responsavel_id, fk_casa_id, roleta_vinculo_ativo
    ) REFERENCES pertencer (fk_usuario_id, fk_casa_id, ativo),
    ADD CONSTRAINT ck_tarefa_roleta CHECK (
        (roleta_expira_em IS NULL OR rotatividade_id IS NOT NULL)
        AND (
            (roleta_responsavel_id IS NULL AND roleta_decidida_em IS NULL
                AND roleta_origem IS NULL AND roleta_atribuida_em IS NULL)
            OR
            (roleta_expira_em IS NOT NULL AND roleta_responsavel_id IS NOT NULL
                AND roleta_decidida_em IS NOT NULL AND roleta_origem IS NOT NULL
                AND roleta_origem IN ('giro', 'balanceamento'))
        )
    );

CREATE INDEX idx_tarefa_roleta_pendente ON tarefa (rotatividade_id, roleta_expira_em, id)
    WHERE roleta_expira_em IS NOT NULL AND roleta_atribuida_em IS NULL;

CREATE INDEX idx_tarefa_roleta_vinculo ON tarefa (
    roleta_responsavel_id, fk_casa_id, roleta_vinculo_ativo
) WHERE roleta_responsavel_id IS NOT NULL;

COMMIT;
