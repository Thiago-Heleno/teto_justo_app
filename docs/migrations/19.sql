-- Aplicar somente após revisar as divergências do endpoint de auditoria de score.
-- O histórico de score_event é canônico; eventos já perdidos não são recriados.
BEGIN;

WITH totais AS (
    SELECT vinculo.fk_usuario_id, vinculo.fk_casa_id,
        COALESCE(SUM(evento.pontuacao), 0)::INT AS score_eventos
    FROM public.pertencer AS vinculo
    LEFT JOIN public.score_event AS evento
        ON evento.fk_usuario_id = vinculo.fk_usuario_id
        AND evento.fk_casa_id = vinculo.fk_casa_id
    GROUP BY vinculo.fk_usuario_id, vinculo.fk_casa_id
)
UPDATE public.pertencer AS vinculo
SET score = totais.score_eventos
FROM totais
WHERE vinculo.fk_usuario_id = totais.fk_usuario_id
    AND vinculo.fk_casa_id = totais.fk_casa_id
    AND vinculo.score IS DISTINCT FROM totais.score_eventos;

COMMIT;
