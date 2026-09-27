BEGIN;

-- A escolha do responsável e as datas são calculadas no backend. A função
-- abaixo somente persiste um conjunto de escritas de forma atômica.
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
    INSERT INTO score_event (fk_usuario_id, fk_casa_id, fk_tarefa_id, pontuacao, criado_em)
        VALUES (p_id_usuario, p_id_casa, p_id_tarefa, p_pontos, p_concluida_em);
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

COMMIT;
