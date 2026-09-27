BEGIN;

    CREATE FUNCTION excluir_tarefa_sem_credito(
        p_id_tarefa UUID
    ) RETURNS BOOLEAN
    LANGUAGE plpgsql
    SECURITY INVOKER
    SET search_path = 'public'
    AS $$
    DECLARE
        tarefa_atual tarefa%ROWTYPE;
    BEGIN
        SELECT * INTO tarefa_atual FROM tarefa
            WHERE id = p_id_tarefa FOR UPDATE;
        IF NOT FOUND THEN
            RETURN FALSE;
        END IF;
        IF tarefa_atual.rotatividade_id IS NOT NULL
            OR EXISTS (SELECT 1 FROM score_event WHERE fk_tarefa_id = p_id_tarefa) THEN
            RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'O histórico desta tarefa deve ser preservado.';
        END IF;

        DELETE FROM atribuida WHERE fk_tarefa_id = p_id_tarefa;
        DELETE FROM tarefa WHERE id = p_id_tarefa;
        RETURN TRUE;
    END;
    $$;

    CREATE FUNCTION excluir_vinculo_sem_credito(
        p_id_usuario UUID,
        p_id_casa UUID
    ) RETURNS BOOLEAN
    LANGUAGE plpgsql
    SECURITY INVOKER
    SET search_path = 'public'
    AS $$
    BEGIN
        PERFORM 1 FROM casa WHERE id = p_id_casa FOR UPDATE;
        IF NOT FOUND THEN
            RETURN FALSE;
        END IF;
        PERFORM 1 FROM pertencer
            WHERE fk_usuario_id = p_id_usuario AND fk_casa_id = p_id_casa FOR UPDATE;
        IF NOT FOUND THEN
            RETURN FALSE;
        END IF;
        IF EXISTS (
            SELECT 1 FROM casa
            WHERE id = p_id_casa AND fk_usuario_id = p_id_usuario
        ) THEN
            RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'O proprietário deve permanecer vinculado à casa.';
        END IF;
        IF EXISTS (
            SELECT 1 FROM score_event
            WHERE fk_usuario_id = p_id_usuario AND fk_casa_id = p_id_casa
        ) THEN
            RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'O histórico de pontos deste morador deve ser preservado.';
        END IF;
        IF EXISTS (
            SELECT 1 FROM atribuida AS atribuicao
            JOIN tarefa AS tarefa_atual ON tarefa_atual.id = atribuicao.fk_tarefa_id
            WHERE atribuicao.fk_usuario_id = p_id_usuario
                AND tarefa_atual.fk_casa_id = p_id_casa
                AND tarefa_atual.estado_atual IN ('pendente', 'atrasada')
        ) THEN
            RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'O morador possui tarefas abertas nesta casa.';
        END IF;
        DELETE FROM pertencer
            WHERE fk_usuario_id = p_id_usuario AND fk_casa_id = p_id_casa;
        UPDATE casa SET rotacao_versao = rotacao_versao + 1 WHERE id = p_id_casa;
        RETURN TRUE;
    END;
    $$;

    REVOKE ALL ON FUNCTION criar_rotatividade(JSONB, UUID[])
        FROM PUBLIC, anon, authenticated;
    GRANT EXECUTE ON FUNCTION criar_rotatividade(JSONB, UUID[])
        TO service_role;
    REVOKE ALL ON FUNCTION registrar_ocorrencia_rotativa(
        UUID, TIMESTAMPTZ, TIMESTAMPTZ, TIMESTAMPTZ, UUID, INT
    ) FROM PUBLIC, anon, authenticated;
    GRANT EXECUTE ON FUNCTION registrar_ocorrencia_rotativa(
        UUID, TIMESTAMPTZ, TIMESTAMPTZ, TIMESTAMPTZ, UUID, INT
    ) TO service_role;
    REVOKE ALL ON FUNCTION excluir_tarefa_sem_credito(UUID)
        FROM PUBLIC, anon, authenticated;
    GRANT EXECUTE ON FUNCTION excluir_tarefa_sem_credito(UUID)
        TO service_role;
    REVOKE ALL ON FUNCTION excluir_vinculo_sem_credito(UUID, UUID)
        FROM PUBLIC, anon, authenticated;
    GRANT EXECUTE ON FUNCTION excluir_vinculo_sem_credito(UUID, UUID)
        TO service_role;

COMMIT;