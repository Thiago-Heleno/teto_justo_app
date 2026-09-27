BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgrelid = 'tarefa'::regclass
            AND tgname = 'trg_tarefa_finalizada_credita_pontos'
            AND NOT tgisinternal
    ) THEN
        RAISE EXCEPTION 'Aplique 15.sql para remover o trigger de crédito antes de 17.sql.';
    END IF;
END;
$$;

-- Datas legadas sem fuso seguem a convenção UTC adotada pelo backend.
ALTER TABLE score_event ALTER COLUMN criado_em DROP DEFAULT;
ALTER TABLE score_event
    ALTER COLUMN criado_em TYPE TIMESTAMPTZ
    USING criado_em AT TIME ZONE 'UTC';
ALTER TABLE score_event ALTER COLUMN criado_em SET DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX idx_score_event_casa_periodo_usuario
    ON score_event (fk_casa_id, criado_em, fk_usuario_id);

-- Os eventos são o histórico do saldo e não podem sumir com a tarefa ou casa.
ALTER TABLE score_event DROP CONSTRAINT fk_scoreevent_casa;
ALTER TABLE score_event ADD CONSTRAINT fk_scoreevent_casa
    FOREIGN KEY (fk_casa_id) REFERENCES casa (id) ON DELETE RESTRICT;
ALTER TABLE score_event DROP CONSTRAINT fk_scoreevent_tarefa;
ALTER TABLE score_event ADD CONSTRAINT fk_scoreevent_tarefa
    FOREIGN KEY (fk_tarefa_id) REFERENCES tarefa (id) ON DELETE RESTRICT;
REVOKE INSERT, UPDATE, DELETE ON score_event FROM PUBLIC, anon, authenticated;
REVOKE INSERT, UPDATE, DELETE ON pertencer FROM PUBLIC, anon, authenticated;

ALTER TABLE casa
    ADD COLUMN timezone TEXT NOT NULL DEFAULT 'America/Sao_Paulo',
    ADD COLUMN rotacao_versao INT NOT NULL DEFAULT 0;

-- Um dono também precisa ter o vínculo que recebe créditos.
INSERT INTO pertencer (fk_usuario_id, fk_casa_id, score)
SELECT fk_usuario_id, id, 0 FROM casa WHERE fk_usuario_id IS NOT NULL
ON CONFLICT (fk_usuario_id, fk_casa_id) DO NOTHING;

UPDATE tarefa SET tipo = 'unitaria' WHERE tipo IS NULL;
UPDATE tarefa SET modo_prazo =
    CASE WHEN prazo_dias IS NULL THEN 'dia_fixo' ELSE 'intervalo' END
WHERE modo_prazo IS NULL;
ALTER TABLE tarefa
    ALTER COLUMN tipo SET NOT NULL,
    ALTER COLUMN modo_prazo SET NOT NULL;

-- Ocorrências podem se sobrepor, portanto a próxima não depende da tolerância atual.
ALTER TABLE tarefa DROP CONSTRAINT ck_tarefa_referencia_inicio;
ALTER TABLE tarefa ADD CONSTRAINT ck_tarefa_referencia_inicio CHECK (
    (referencia_inicio = 'criacao' AND proxima_ocorrencia IS NULL)
    OR (referencia_inicio = 'ocorrencia' AND data_inicio IS NOT NULL
        AND prazo_dias IS NOT NULL)
);

CREATE TABLE rotatividade (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_casa_id UUID NOT NULL REFERENCES casa (id) ON DELETE RESTRICT,
    fk_usuario_id UUID NOT NULL REFERENCES usuario (id) ON DELETE RESTRICT,
    timezone TEXT NOT NULL,
    nome TEXT NOT NULL CHECK (length(trim(nome)) > 0),
    descricao TEXT,
    dificuldade INT NOT NULL CHECK (dificuldade IN (1, 2, 3)),
    pontuacao INT NOT NULL CHECK (
        pontuacao = CASE dificuldade WHEN 1 THEN 10 WHEN 2 THEN 25 WHEN 3 THEN 50 END
    ),
    prazo_dias INT NOT NULL CHECK (prazo_dias BETWEEN 1 AND 5),
    atraso_maximo INT NOT NULL CHECK (atraso_maximo BETWEEN 1 AND 5),
    modo_prazo VARCHAR(9) NOT NULL CHECK (modo_prazo IN ('dia_fixo', 'intervalo')),
    dias_semana INT[] NOT NULL CHECK (
        cardinality(dias_semana) BETWEEN 1 AND 7
        AND dias_semana <@ ARRAY[1, 2, 3, 4, 5, 6, 7]
    ),
    intervalo_semanas INT NOT NULL CHECK (intervalo_semanas BETWEEN 1 AND 4),
    semana_ancora DATE NOT NULL,
    ativa BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE rotatividade_participante (
    fk_rotatividade_id UUID NOT NULL REFERENCES rotatividade (id) ON DELETE RESTRICT,
    fk_usuario_id UUID NOT NULL REFERENCES usuario (id) ON DELETE RESTRICT,
    ordem INT NOT NULL CHECK (ordem > 0),
    PRIMARY KEY (fk_rotatividade_id, fk_usuario_id),
    UNIQUE (fk_rotatividade_id, ordem)
);
REVOKE ALL ON rotatividade, rotatividade_participante
    FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON rotatividade, rotatividade_participante TO service_role;

ALTER TABLE tarefa
    ADD COLUMN rotatividade_id UUID REFERENCES rotatividade (id) ON DELETE RESTRICT,
    ADD COLUMN ocorrencia_em TIMESTAMPTZ,
    ADD COLUMN timezone TEXT;
ALTER TABLE tarefa ADD CONSTRAINT ck_tarefa_ocorrencia CHECK (
    (rotatividade_id IS NULL AND ocorrencia_em IS NULL)
    OR (rotatividade_id IS NOT NULL AND ocorrencia_em IS NOT NULL AND tipo = 'rotativa')
);
CREATE UNIQUE INDEX uq_tarefa_rotatividade_ocorrencia
    ON tarefa (rotatividade_id, ocorrencia_em)
    WHERE rotatividade_id IS NOT NULL;
CREATE INDEX idx_tarefa_rotatividade_casa_mes
    ON tarefa (fk_casa_id, ocorrencia_em)
    WHERE rotatividade_id IS NOT NULL;

COMMIT;
