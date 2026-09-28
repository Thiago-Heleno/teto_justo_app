BEGIN;

-- O legado guardava apenas o valor líquido da conclusão.
-- Mantemos esses valores históricos; a decomposição anterior não é recuperável.
ALTER TABLE score_event DROP CONSTRAINT score_event_tipo_check;
UPDATE score_event SET tipo = 'COMPLETION_AWARD' WHERE tipo = 'credito';
UPDATE score_event SET tipo = 'REVERSAL' WHERE tipo = 'reversal';
ALTER TABLE score_event ADD CONSTRAINT score_event_tipo_check
    CHECK (tipo IN ('COMPLETION_AWARD', 'LATE_PENALTY', 'REVERSAL'));
DROP INDEX uq_score_event_credito;
CREATE UNIQUE INDEX uq_score_event_credito ON score_event (fk_usuario_id, fk_tarefa_id)
    WHERE tipo = 'COMPLETION_AWARD';
CREATE UNIQUE INDEX uq_score_event_penalty ON score_event (fk_usuario_id, fk_tarefa_id)
    WHERE tipo = 'LATE_PENALTY';
CREATE UNIQUE INDEX uq_score_event_reversal ON score_event (fk_usuario_id, fk_tarefa_id)
    WHERE tipo = 'REVERSAL';

CREATE OR REPLACE FUNCTION registrar_conclusao_tarefa(
    p_id_tarefa UUID,
    p_id_usuario UUID,
    p_pontos INT,
    p_concluida_em TIMESTAMPTZ,
    p_dificuldade INT,
    p_atraso_maximo INT,
    p_data_fim TIMESTAMP,
    p_data_inicio TIMESTAMP,
    p_id_casa UUID
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = 'public'
AS $$
DECLARE
    tarefa_atual tarefa%ROWTYPE;
    quantidade_responsaveis INT;
    responsavel_valido BOOLEAN;
    saldo_atual INT;
BEGIN
    IF p_pontos IS NULL OR p_pontos < 0 OR p_concluida_em IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Conclusão inválida.';
    END IF;

    SELECT * INTO tarefa_atual FROM tarefa WHERE id = p_id_tarefa FOR UPDATE;
    IF NOT FOUND OR tarefa_atual.estado_atual NOT IN ('pendente', 'atrasada') THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'A tarefa não está disponível para conclusão.';
    END IF;
    IF tarefa_atual.dificuldade IS DISTINCT FROM p_dificuldade
        OR tarefa_atual.atraso_maximo IS DISTINCT FROM p_atraso_maximo
        OR tarefa_atual.data_fim IS DISTINCT FROM p_data_fim
        OR tarefa_atual.data_inicio IS DISTINCT FROM p_data_inicio
        OR tarefa_atual.fk_casa_id IS DISTINCT FROM p_id_casa THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'A tarefa mudou. Atualize antes de concluir.';
    END IF;

    IF p_pontos > tarefa_atual.pontuacao THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Pontuação excede o valor da tarefa.';
    END IF;

    PERFORM 1 FROM atribuida WHERE fk_tarefa_id = p_id_tarefa FOR UPDATE;
    SELECT COUNT(*), BOOL_AND(fk_usuario_id = p_id_usuario)
        INTO quantidade_responsaveis, responsavel_valido
        FROM atribuida WHERE fk_tarefa_id = p_id_tarefa;
    IF quantidade_responsaveis <> 1 OR responsavel_valido IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'O responsável pela tarefa mudou.';
    END IF;
    IF EXISTS (SELECT 1 FROM score_event WHERE fk_tarefa_id = p_id_tarefa) THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Esta tarefa já possui crédito registrado.';
    END IF;

    UPDATE pertencer SET score = COALESCE(score, 0) + p_pontos
        WHERE fk_usuario_id = p_id_usuario AND fk_casa_id = p_id_casa
        RETURNING score INTO saldo_atual;
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'O responsável precisa ter vínculo de morador na casa.';
    END IF;
    INSERT INTO score_event (fk_usuario_id, fk_casa_id, fk_tarefa_id, pontuacao, criado_em, tipo)
        VALUES (p_id_usuario, p_id_casa, p_id_tarefa, tarefa_atual.pontuacao,
            p_concluida_em, 'COMPLETION_AWARD');
    IF p_pontos < tarefa_atual.pontuacao THEN
        INSERT INTO score_event (fk_usuario_id, fk_casa_id, fk_tarefa_id, pontuacao, criado_em, tipo)
            VALUES (p_id_usuario, p_id_casa, p_id_tarefa,
                p_pontos - tarefa_atual.pontuacao, p_concluida_em, 'LATE_PENALTY');
    END IF;
    UPDATE tarefa SET estado_atual = 'finalizado',
        concluida_em = p_concluida_em AT TIME ZONE 'UTC'
        WHERE id = p_id_tarefa RETURNING * INTO tarefa_atual;

    RETURN to_jsonb(tarefa_atual) || jsonb_build_object(
        'resultado_pontuacao', jsonb_build_object(
            'pontos_possiveis', tarefa_atual.pontuacao,
            'pontos_ganhos', p_pontos,
            'saldo_atual', saldo_atual
        )
    );
END;
$$;

CREATE FUNCTION reabrir_tarefa_com_reversao(p_id_tarefa UUID) RETURNS JSONB
LANGUAGE plpgsql SECURITY INVOKER SET search_path = 'public'
AS $$
DECLARE
    tarefa_atual tarefa%ROWTYPE;
    credito score_event%ROWTYPE;
    pontos_liquidos INT;
BEGIN
    SELECT * INTO tarefa_atual FROM tarefa WHERE id = p_id_tarefa FOR UPDATE;
    IF NOT FOUND OR tarefa_atual.estado_atual <> 'finalizado' THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Tarefa não está finalizada.';
    END IF;
    SELECT * INTO credito FROM score_event
        WHERE fk_tarefa_id = p_id_tarefa AND tipo = 'COMPLETION_AWARD' FOR UPDATE;
    IF NOT FOUND OR EXISTS (
        SELECT 1 FROM score_event WHERE fk_tarefa_id = p_id_tarefa AND tipo = 'REVERSAL'
    ) THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Crédito ausente ou já revertido.';
    END IF;
    SELECT COALESCE(SUM(pontuacao), 0)::INT INTO pontos_liquidos
        FROM score_event WHERE fk_tarefa_id = p_id_tarefa
        AND tipo IN ('COMPLETION_AWARD', 'LATE_PENALTY');
    UPDATE pertencer SET score = COALESCE(score, 0) - pontos_liquidos
        WHERE fk_usuario_id = credito.fk_usuario_id AND fk_casa_id = credito.fk_casa_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Vínculo de morador não encontrado.';
    END IF;
    INSERT INTO score_event (fk_usuario_id, fk_casa_id, fk_tarefa_id, pontuacao, tipo)
        VALUES (credito.fk_usuario_id, credito.fk_casa_id, p_id_tarefa,
            -pontos_liquidos, 'REVERSAL');
    UPDATE tarefa SET estado_atual = 'pendente', concluida_em = NULL
        WHERE id = p_id_tarefa RETURNING * INTO tarefa_atual;
    RETURN to_jsonb(tarefa_atual);
END;
$$;
REVOKE ALL ON FUNCTION reabrir_tarefa_com_reversao(UUID) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION reabrir_tarefa_com_reversao(UUID) TO service_role;

COMMIT;