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

DROP TRIGGER IF EXISTS TRG_Tarefa_Finalizada_Credita_Pontos ON public.tarefa;
DROP FUNCTION IF EXISTS public.fn_tarefa_finalizada_credita_pontos();

-- Persistência atômica: recebe o resultado já calculado pelo backend Python.
-- Não calcula dificuldade, dias de atraso, taxas ou arredondamento.
CREATE FUNCTION public.registrar_conclusao_tarefa(
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
BEGIN
    IF p_pontos IS NULL OR p_pontos < 0 OR p_concluida_em IS NULL THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'Conclusão inválida.';
    END IF;

    SELECT * INTO tarefa_atual FROM public.tarefa WHERE id = p_id_tarefa FOR UPDATE;
    IF NOT FOUND OR tarefa_atual.estado_atual NOT IN ('pendente', 'atrasada') THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'A tarefa não está disponível para conclusão.';
    END IF;

    -- Se as regras mudaram durante o cálculo, o backend deve consultar novamente.
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
        WHERE fk_usuario_id = p_id_usuario AND fk_casa_id = p_id_casa;
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = 'PT409', MESSAGE = 'O responsável precisa ter vínculo de morador na casa.';
    END IF;

    INSERT INTO public.score_event (fk_usuario_id, fk_casa_id, fk_tarefa_id, pontuacao, criado_em)
        VALUES (p_id_usuario, p_id_casa, p_id_tarefa, p_pontos, p_concluida_em AT TIME ZONE 'UTC');

    UPDATE public.tarefa SET estado_atual = 'finalizado',
        concluida_em = p_concluida_em AT TIME ZONE 'UTC'
        WHERE id = p_id_tarefa RETURNING * INTO tarefa_atual;
    RETURN to_jsonb(tarefa_atual);
END;
$$;

-- Somente o backend com a chave service_role pode fornecer os pontos calculados.
REVOKE ALL ON FUNCTION public.registrar_conclusao_tarefa(
    UUID, UUID, INT, TIMESTAMPTZ, INT, INT, TIMESTAMP, TIMESTAMP, UUID
) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.registrar_conclusao_tarefa(
    UUID, UUID, INT, TIMESTAMPTZ, INT, INT, TIMESTAMP, TIMESTAMP, UUID
) TO service_role;

COMMIT;
