BEGIN;

-- A escolha do responsável e as datas são calculadas no backend. A função
-- abaixo somente persiste um conjunto de escritas de forma atômica.
CREATE FUNCTION criar_rotatividade(
    p_config JSONB,
    p_participantes UUID[]
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = 'public'
AS $$
DECLARE
    configuracao rotatividade%ROWTYPE;
    id_casa UUID;
    fuso_casa TEXT;
BEGIN
    id_casa := (p_config->>'fk_casa_id')::UUID;
    SELECT timezone INTO fuso_casa FROM casa
        WHERE id = id_casa FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Casa indisponível.';
    END IF;
    IF p_config->>'timezone_esperado' IS DISTINCT FROM fuso_casa THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Fuso da casa mudou. Recalcule a agenda.';
    END IF;
    IF p_participantes IS NULL OR cardinality(p_participantes) < 2
        OR (SELECT COUNT(DISTINCT participante.id)
            FROM unnest(p_participantes) AS participante(id))
            <> cardinality(p_participantes) THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Selecione moradores diferentes para o rodízio.';
    END IF;
    IF EXISTS (
        SELECT 1 FROM unnest(p_participantes) AS participante(id)
        LEFT JOIN pertencer AS vinculo
            ON vinculo.fk_usuario_id = participante.id AND vinculo.fk_casa_id = id_casa
        WHERE vinculo.fk_usuario_id IS NULL
    ) THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Todos os participantes precisam morar na casa.';
    END IF;

    INSERT INTO rotatividade (
        fk_casa_id, fk_usuario_id, timezone, nome, descricao, dificuldade, pontuacao,
        prazo_dias, atraso_maximo, modo_prazo, dias_semana, intervalo_semanas,
        semana_ancora
    ) VALUES (
        id_casa,
        (p_config->>'fk_usuario_id')::UUID,
        fuso_casa,
        p_config->>'nome',
        p_config->>'descricao',
        (p_config->>'dificuldade')::INT,
        (p_config->>'pontuacao')::INT,
        (p_config->>'prazo_dias')::INT,
        (p_config->>'atraso_maximo')::INT,
        p_config->>'modo_prazo',
        ARRAY(SELECT jsonb_array_elements_text(p_config->'dias_semana')::INT),
        (p_config->>'intervalo_semanas')::INT,
        (p_config->>'semana_ancora')::DATE
    ) RETURNING * INTO configuracao;

    INSERT INTO rotatividade_participante (
        fk_rotatividade_id, fk_usuario_id, ordem
    )
    SELECT configuracao.id, participante.id, participante.ordem::INT
    FROM unnest(p_participantes) WITH ORDINALITY AS participante(id, ordem);

    RETURN to_jsonb(configuracao);
END;
$$;

COMMIT;
