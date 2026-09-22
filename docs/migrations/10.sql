BEGIN;

-- atraso_maximo passa a ser obrigatorio e positivo: define em quantos dias
-- de atraso a tarefa perde 100% dos pontos (e o backend passa a marca-la
-- como 'nao_feito').
ALTER TABLE tarefa
    ALTER COLUMN atraso_maximo SET NOT NULL;

ALTER TABLE tarefa
    ADD CONSTRAINT CK_Tarefa_atraso_maximo CHECK (atraso_maximo > 0);

-- A taxa diaria de desconto passa a ser 100% / atraso_maximo (variavel por
-- tarefa, proporcional ao prazo de tolerancia dela), substituindo a taxa
-- fixa por tipo_de_penalidade (1=-10%/dia, 2=-20%/dia, 3=-30%/dia,
-- 4=-40%/dia). No atraso_maximo-esimo dia de atraso a perda ja chega a
-- 100%, zerando a pontuacao.
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

    taxa_diaria := 100.0 / NEW.atraso_maximo;

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

COMMIT;
