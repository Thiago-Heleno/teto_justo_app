BEGIN;

-- padronizando o tipo de calculo da pontuação

-- dificuldade (peso) passa a ser obrigatoria e restrita a 1, 2 ou 3.
ALTER TABLE tarefa
    ALTER COLUMN dificuldade SET NOT NULL;

ALTER TABLE tarefa
    DROP CONSTRAINT IF EXISTS CK_Tarefa_dificuldade;

ALTER TABLE tarefa
    ADD CONSTRAINT CK_Tarefa_dificuldade CHECK (dificuldade IN (1, 2, 3));

-- Trigger de credito passa a derivar pontos_base de dificuldade (peso),
-- em vez de ler NEW.pontuacao.
CREATE OR REPLACE FUNCTION fn_tarefa_finalizada_credita_pontos()
RETURNS TRIGGER AS $$
DECLARE
    dias_atraso INT;
    taxa_diaria NUMERIC;
    percentual NUMERIC;
    pontos_base INT;
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

    pontos_base := CASE NEW.dificuldade
        WHEN 1 THEN 10
        WHEN 2 THEN 25
        WHEN 3 THEN 50
    END;

    pontos_creditados := ROUND(pontos_base * percentual / 100.0);

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