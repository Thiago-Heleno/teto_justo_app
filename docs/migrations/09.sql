BEGIN;

-- Ao finalizar uma tarefa: grava concluida_em, credita pontos (com desconto
-- por atraso) em score_event e soma em Pertencer.score de cada responsavel
-- atribuido em atribuida.
--
-- Desconto por atraso: taxa diaria fixa por tipo_de_penalidade (1=-10%/dia,
-- 2=-20%/dia, 3=-30%/dia, 4=-40%/dia) multiplicada pelos dias de atraso,
-- com piso em 0%. Sem tipo_de_penalidade definido, nao ha desconto
-- (pontuacao cheia).
CREATE OR REPLACE FUNCTION fn_tarefa_finalizada_credita_pontos()
RETURNS TRIGGER AS $$
DECLARE
    dias_atraso INT;
    taxa_diaria NUMERIC;
    percentual NUMERIC;
    pontos_creditados INT;
    id_usuario UUID;
BEGIN
    NEW.concluida_em := NOW();

    dias_atraso := GREATEST(
        0,
        FLOOR(EXTRACT(EPOCH FROM (NOW() - NEW.data_fim)) / 86400)
    )::INT;

    taxa_diaria := CASE NEW.tipo_de_penalidade
        WHEN 1 THEN 10
        WHEN 2 THEN 20
        WHEN 3 THEN 30
        WHEN 4 THEN 40
        ELSE 0
    END;

    percentual := GREATEST(0, 100 - dias_atraso * taxa_diaria);

    pontos_creditados := ROUND(NEW.pontuacao * percentual / 100.0);

    FOR id_usuario IN
        SELECT fk_usuario_id FROM atribuida WHERE fk_tarefa_id = NEW.id
    LOOP
        INSERT INTO score_event (fk_usuario_id, fk_casa_id, fk_tarefa_id, pontuacao)
        VALUES (id_usuario, NEW.fk_casa_id, NEW.id, pontos_creditados)
        ON CONFLICT (fk_usuario_id, fk_tarefa_id) DO NOTHING;

        IF FOUND THEN
            UPDATE pertencer
               SET score = score + pontos_creditados
             WHERE fk_usuario_id = id_usuario
               AND fk_casa_id = NEW.fk_casa_id;
        END IF;
    END LOOP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER TRG_Tarefa_Finalizada_Credita_Pontos
    BEFORE UPDATE ON tarefa
    FOR EACH ROW
    WHEN (OLD.estado_atual IS DISTINCT FROM 'finalizado' AND NEW.estado_atual = 'finalizado')
    EXECUTE FUNCTION fn_tarefa_finalizada_credita_pontos();

COMMIT;
