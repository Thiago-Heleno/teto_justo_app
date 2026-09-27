BEGIN;

    CREATE FUNCTION registrar_ocorrencia_rotativa(
        p_id_rotatividade UUID,
        p_ocorrencia_em TIMESTAMPTZ,
        p_data_inicio TIMESTAMPTZ,
        p_data_fim TIMESTAMPTZ,
        p_id_usuario UUID,
        p_versao_casa INT
    ) RETURNS JSONB
    LANGUAGE plpgsql
    SECURITY INVOKER
    SET search_path = 'public'
    AS $$
    DECLARE
        configuracao rotatividade%ROWTYPE;
        tarefa_atual tarefa%ROWTYPE;
        versao_atual INT;
    BEGIN
        SELECT * INTO configuracao FROM rotatividade
            WHERE id = p_id_rotatividade;
        IF NOT FOUND OR NOT configuracao.ativa THEN
            RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Rodízio indisponível.';
        END IF;

        SELECT rotacao_versao INTO versao_atual FROM casa
            WHERE id = configuracao.fk_casa_id FOR UPDATE;
        IF NOT FOUND THEN
            RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Casa indisponível.';
        END IF;

        SELECT * INTO tarefa_atual FROM tarefa
            WHERE rotatividade_id = p_id_rotatividade AND ocorrencia_em = p_ocorrencia_em;
        IF FOUND THEN
            RETURN to_jsonb(tarefa_atual);
        END IF;

        IF versao_atual IS DISTINCT FROM p_versao_casa THEN
            RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Rodízio alterado. Recalcule a distribuição.';
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM rotatividade_participante AS participante
            JOIN pertencer AS vinculo
                ON vinculo.fk_usuario_id = participante.fk_usuario_id
                AND vinculo.fk_casa_id = configuracao.fk_casa_id
            WHERE participante.fk_rotatividade_id = p_id_rotatividade
                AND participante.fk_usuario_id = p_id_usuario
        ) THEN
            RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Responsável não elegível para esta ocorrência.';
        END IF;

        INSERT INTO tarefa (
            nome, descricao, estado_atual, dificuldade, pontuacao, prazo_dias,
            atraso_maximo, modo_prazo, tipo, referencia_inicio,
            data_inicio, data_fim, fk_casa_id, fk_usuario_id,
            rotatividade_id, ocorrencia_em, timezone
        ) VALUES (
            configuracao.nome, configuracao.descricao, 'pendente',
            configuracao.dificuldade, configuracao.pontuacao, configuracao.prazo_dias,
            configuracao.atraso_maximo, configuracao.modo_prazo, 'rotativa', 'ocorrencia',
            p_data_inicio AT TIME ZONE 'UTC', p_data_fim AT TIME ZONE 'UTC',
            configuracao.fk_casa_id, configuracao.fk_usuario_id,
            configuracao.id, p_ocorrencia_em, configuracao.timezone
        ) RETURNING * INTO tarefa_atual;

        INSERT INTO atribuida (fk_usuario_id, fk_tarefa_id)
            VALUES (p_id_usuario, tarefa_atual.id);
        UPDATE casa SET rotacao_versao = rotacao_versao + 1
            WHERE id = configuracao.fk_casa_id;

        RETURN to_jsonb(tarefa_atual);
    END;
    $$;

COMMIT;