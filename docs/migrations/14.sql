BEGIN;

-- Pontuação-base derivada da dificuldade; créditos históricos não são recalculados.
ALTER TABLE tarefa DROP CONSTRAINT CK_Tarefa_pontuacao;
UPDATE tarefa SET pontuacao = CASE dificuldade WHEN 1 THEN 10 WHEN 2 THEN 25 WHEN 3 THEN 50 END;
ALTER TABLE tarefa ADD CONSTRAINT CK_Tarefa_pontuacao
    CHECK (pontuacao = CASE dificuldade WHEN 1 THEN 10 WHEN 2 THEN 25 WHEN 3 THEN 50 END);

ALTER TABLE tarefa
    ADD COLUMN prazo_dias INT CHECK (prazo_dias BETWEEN 1 AND 5),
    ADD COLUMN referencia_inicio TEXT NOT NULL DEFAULT 'criacao'
        CHECK (referencia_inicio IN ('criacao', 'ocorrencia')),
    ADD COLUMN proxima_ocorrencia TIMESTAMPTZ;

-- As colunas legadas sem fuso são interpretadas como UTC, como no backend.
-- Não inventa uma duração para tarefas antigas que só possuíam data_fim.
UPDATE tarefa SET data_inicio = criado_em WHERE data_inicio IS NULL;
ALTER TABLE tarefa ADD CONSTRAINT CK_Tarefa_prazo_calculado CHECK (
    prazo_dias IS NULL OR (
        data_inicio IS NOT NULL AND data_fim IS NOT NULL
        AND data_fim = data_inicio + prazo_dias * INTERVAL '1 day'
    )
);
ALTER TABLE tarefa ADD CONSTRAINT CK_Tarefa_referencia_inicio CHECK (
    (referencia_inicio = 'criacao' AND proxima_ocorrencia IS NULL)
    OR (referencia_inicio = 'ocorrencia' AND data_inicio IS NOT NULL
        AND prazo_dias IS NOT NULL AND proxima_ocorrencia IS NOT NULL
        AND EXTRACT(EPOCH FROM (proxima_ocorrencia - (data_fim AT TIME ZONE 'UTC')))
            > atraso_maximo::NUMERIC * 86400)
);

-- O único crédito continua no trigger de conclusão, sem descontar o saldo diariamente.
CREATE OR REPLACE FUNCTION fn_tarefa_finalizada_credita_pontos()
RETURNS TRIGGER AS $$
DECLARE
    dias_atraso NUMERIC;
    divisor NUMERIC;
    pontos_base INT;
    pontos_creditados INT;
    id_usuario UUID;
BEGIN
    NEW.concluida_em := NOW() AT TIME ZONE 'UTC';
    dias_atraso := GREATEST(
        0, CEIL(EXTRACT(EPOCH FROM (NOW() - (NEW.data_fim AT TIME ZONE 'UTC'))) / 86400)
    );
    divisor := NEW.atraso_maximo::NUMERIC + 1;
    pontos_base := CASE NEW.dificuldade WHEN 1 THEN 10 WHEN 2 THEN 25 WHEN 3 THEN 50 END;
    pontos_creditados := ROUND(pontos_base * GREATEST(0, divisor - dias_atraso) / divisor);

    FOR id_usuario IN
        SELECT fk_usuario_id FROM atribuida WHERE fk_tarefa_id = NEW.id
    LOOP
        INSERT INTO score_event (fk_usuario_id, fk_casa_id, fk_tarefa_id, pontuacao)
        VALUES (id_usuario, NEW.fk_casa_id, NEW.id, pontos_creditados)
        ON CONFLICT (fk_usuario_id, fk_tarefa_id) DO NOTHING;

        IF FOUND THEN
            UPDATE pertencer
               SET score = score + pontos_creditados
             WHERE fk_usuario_id = id_usuario AND fk_casa_id = NEW.fk_casa_id;
        END IF;
    END LOOP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMIT;
