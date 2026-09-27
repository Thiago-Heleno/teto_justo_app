BEGIN;

-- A escolha do responsável e as datas são calculadas no backend. As funções
-- abaixo somente persistem um conjunto de escritas de forma atômica.
CREATE FUNCTION public.criar_rotatividade(
    p_config JSONB,
    p_participantes UUID[]
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    configuracao public.rotatividade%ROWTYPE;
    id_casa UUID;
    fuso_casa TEXT;
BEGIN
    id_casa := (p_config->>'fk_casa_id')::UUID;
    SELECT timezone INTO fuso_casa FROM public.casa
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
        LEFT JOIN public.pertencer AS vinculo
            ON vinculo.fk_usuario_id = participante.id AND vinculo.fk_casa_id = id_casa
        WHERE vinculo.fk_usuario_id IS NULL
    ) THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Todos os participantes precisam morar na casa.';
    END IF;

    INSERT INTO public.rotatividade (
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

    INSERT INTO public.rotatividade_participante (
        fk_rotatividade_id, fk_usuario_id, ordem
    )
    SELECT configuracao.id, participante.id, participante.ordem::INT
    FROM unnest(p_participantes) WITH ORDINALITY AS participante(id, ordem);

    RETURN to_jsonb(configuracao);
END;
$$;

CREATE FUNCTION public.registrar_ocorrencia_rotativa(
    p_id_rotatividade UUID,
    p_ocorrencia_em TIMESTAMPTZ,
    p_data_inicio TIMESTAMPTZ,
    p_data_fim TIMESTAMPTZ,
    p_id_usuario UUID,
    p_versao_casa INT
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    configuracao public.rotatividade%ROWTYPE;
    tarefa_atual public.tarefa%ROWTYPE;
    versao_atual INT;
BEGIN
    SELECT * INTO configuracao FROM public.rotatividade
        WHERE id = p_id_rotatividade;
    IF NOT FOUND OR NOT configuracao.ativa THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Rodízio indisponível.';
    END IF;

    SELECT rotacao_versao INTO versao_atual FROM public.casa
        WHERE id = configuracao.fk_casa_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Casa indisponível.';
    END IF;

    SELECT * INTO tarefa_atual FROM public.tarefa
        WHERE rotatividade_id = p_id_rotatividade AND ocorrencia_em = p_ocorrencia_em;
    IF FOUND THEN
        RETURN to_jsonb(tarefa_atual);
    END IF;

    IF versao_atual IS DISTINCT FROM p_versao_casa THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Rodízio alterado. Recalcule a distribuição.';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.rotatividade_participante AS participante
        JOIN public.pertencer AS vinculo
            ON vinculo.fk_usuario_id = participante.fk_usuario_id
            AND vinculo.fk_casa_id = configuracao.fk_casa_id
        WHERE participante.fk_rotatividade_id = p_id_rotatividade
            AND participante.fk_usuario_id = p_id_usuario
    ) THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Responsável não elegível para esta ocorrência.';
    END IF;

    INSERT INTO public.tarefa (
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

    INSERT INTO public.atribuida (fk_usuario_id, fk_tarefa_id)
        VALUES (p_id_usuario, tarefa_atual.id);
    UPDATE public.casa SET rotacao_versao = rotacao_versao + 1
        WHERE id = configuracao.fk_casa_id;

    RETURN to_jsonb(tarefa_atual);
END;
$$;

CREATE FUNCTION public.excluir_tarefa_sem_credito(
    p_id_tarefa UUID
) RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
    tarefa_atual public.tarefa%ROWTYPE;
BEGIN
    SELECT * INTO tarefa_atual FROM public.tarefa
        WHERE id = p_id_tarefa FOR UPDATE;
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    IF tarefa_atual.rotatividade_id IS NOT NULL
        OR EXISTS (SELECT 1 FROM public.score_event WHERE fk_tarefa_id = p_id_tarefa) THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'O histórico desta tarefa deve ser preservado.';
    END IF;

    DELETE FROM public.atribuida WHERE fk_tarefa_id = p_id_tarefa;
    DELETE FROM public.tarefa WHERE id = p_id_tarefa;
    RETURN TRUE;
END;
$$;

CREATE FUNCTION public.excluir_vinculo_sem_credito(
    p_id_usuario UUID,
    p_id_casa UUID
) RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
    PERFORM 1 FROM public.casa WHERE id = p_id_casa FOR UPDATE;
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    PERFORM 1 FROM public.pertencer
        WHERE fk_usuario_id = p_id_usuario AND fk_casa_id = p_id_casa FOR UPDATE;
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    IF EXISTS (
        SELECT 1 FROM public.casa
        WHERE id = p_id_casa AND fk_usuario_id = p_id_usuario
    ) THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'O proprietário deve permanecer vinculado à casa.';
    END IF;
    IF EXISTS (
        SELECT 1 FROM public.score_event
        WHERE fk_usuario_id = p_id_usuario AND fk_casa_id = p_id_casa
    ) THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'O histórico de pontos deste morador deve ser preservado.';
    END IF;
    IF EXISTS (
        SELECT 1 FROM public.atribuida AS atribuicao
        JOIN public.tarefa AS tarefa_atual ON tarefa_atual.id = atribuicao.fk_tarefa_id
        WHERE atribuicao.fk_usuario_id = p_id_usuario
            AND tarefa_atual.fk_casa_id = p_id_casa
            AND tarefa_atual.estado_atual IN ('pendente', 'atrasada')
    ) THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'O morador possui tarefas abertas nesta casa.';
    END IF;
    DELETE FROM public.pertencer
        WHERE fk_usuario_id = p_id_usuario AND fk_casa_id = p_id_casa;
    UPDATE public.casa SET rotacao_versao = rotacao_versao + 1 WHERE id = p_id_casa;
    RETURN TRUE;
END;
$$;

CREATE OR REPLACE FUNCTION public.registrar_conclusao_tarefa(
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
SET search_path = ''
AS $$
DECLARE
    tarefa_atual public.tarefa%ROWTYPE;
    quantidade_responsaveis INT;
    responsavel_valido BOOLEAN;
    saldo_atual INT;
BEGIN
    IF p_pontos IS NULL OR p_pontos < 0 OR p_concluida_em IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Conclusão inválida.';
    END IF;

    SELECT * INTO tarefa_atual FROM public.tarefa WHERE id = p_id_tarefa FOR UPDATE;
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

    PERFORM 1 FROM public.atribuida WHERE fk_tarefa_id = p_id_tarefa FOR UPDATE;
    SELECT COUNT(*), BOOL_AND(fk_usuario_id = p_id_usuario)
        INTO quantidade_responsaveis, responsavel_valido
        FROM public.atribuida WHERE fk_tarefa_id = p_id_tarefa;
    IF quantidade_responsaveis <> 1 OR responsavel_valido IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'O responsável pela tarefa mudou.';
    END IF;
    IF EXISTS (SELECT 1 FROM public.score_event WHERE fk_tarefa_id = p_id_tarefa) THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Esta tarefa já possui crédito registrado.';
    END IF;

    UPDATE public.pertencer SET score = COALESCE(score, 0) + p_pontos
        WHERE fk_usuario_id = p_id_usuario AND fk_casa_id = p_id_casa
        RETURNING score INTO saldo_atual;
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'O responsável precisa ter vínculo de morador na casa.';
    END IF;
    INSERT INTO public.score_event (fk_usuario_id, fk_casa_id, fk_tarefa_id, pontuacao, criado_em)
        VALUES (p_id_usuario, p_id_casa, p_id_tarefa, p_pontos, p_concluida_em);
    UPDATE public.tarefa SET estado_atual = 'finalizado',
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

REVOKE ALL ON FUNCTION public.criar_rotatividade(JSONB, UUID[])
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.criar_rotatividade(JSONB, UUID[])
    TO service_role;
REVOKE ALL ON FUNCTION public.registrar_ocorrencia_rotativa(
    UUID, TIMESTAMPTZ, TIMESTAMPTZ, TIMESTAMPTZ, UUID, INT
) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.registrar_ocorrencia_rotativa(
    UUID, TIMESTAMPTZ, TIMESTAMPTZ, TIMESTAMPTZ, UUID, INT
) TO service_role;
REVOKE ALL ON FUNCTION public.excluir_tarefa_sem_credito(UUID)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.excluir_tarefa_sem_credito(UUID)
    TO service_role;
REVOKE ALL ON FUNCTION public.excluir_vinculo_sem_credito(UUID, UUID)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.excluir_vinculo_sem_credito(UUID, UUID)
    TO service_role;

COMMIT;
