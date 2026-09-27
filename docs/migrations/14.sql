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