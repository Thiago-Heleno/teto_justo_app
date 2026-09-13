-- Corrige a conversao INT -> UUID do esquema criado por 01.sql (public).
-- Preserva os relacionamentos existentes. Executar o arquivo inteiro.
-- Se todas as colunas ja forem UUID, nao altera os registros.
-- Nao recupera vinculos apagados pela versao antiga desta migracao.
BEGIN;
SET LOCAL search_path = public, pg_catalog;
SET LOCAL lock_timeout = '10s';

DO $migration$
DECLARE
    coluna RECORD;
    entidade TEXT;
    tipo TEXT;
    sem_mapeamento BOOLEAN;
    total_uuid INTEGER := 0;
    total_int INTEGER := 0;
    mapa JSONB;
    mapas JSONB := '{}'::jsonb;
BEGIN
    -- Impede gravacoes concorrentes entre a leitura dos IDs e a conversao.
    LOCK TABLE public.usuario, public.casa, public.tarefa, public.sessao,
               public.pertencer, public.atribuida IN ACCESS EXCLUSIVE MODE;

    FOR coluna IN
        SELECT * FROM (VALUES
            ('casa', 'id'), ('usuario', 'id'), ('tarefa', 'id'), ('sessao', 'id'),
            ('casa', 'fk_usuario_id'), ('tarefa', 'fk_casa_id'),
            ('tarefa', 'fk_usuario_id'), ('sessao', 'fk_usuario_id'),
            ('pertencer', 'fk_usuario_id'), ('pertencer', 'fk_casa_id'),
            ('atribuida', 'fk_usuario_id'), ('atribuida', 'fk_tarefa_id')
        ) AS colunas(tabela, nome)
    LOOP
        SELECT data_type INTO tipo FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = coluna.tabela
          AND column_name = coluna.nome;
        IF tipo = 'uuid' THEN
            total_uuid := total_uuid + 1;
        ELSIF tipo = 'integer' THEN
            total_int := total_int + 1;
        ELSE
            RAISE EXCEPTION 'Coluna %.% ausente ou com tipo inesperado: %',
                coluna.tabela, coluna.nome, tipo;
        END IF;
    END LOOP;

    IF total_uuid = 12 THEN
        RAISE NOTICE '02.sql: IDs ja sao UUID; nenhuma conversao executada.';
        RETURN;
    ELSIF total_int <> 12 THEN
        RAISE EXCEPTION 'Esquema parcialmente convertido. Revisar antes de migrar.';
    END IF;

    -- Um UUID por registro original, reutilizado em todas as referencias.
    FOREACH entidade IN ARRAY ARRAY['usuario', 'casa', 'tarefa', 'sessao']
    LOOP
        EXECUTE format(
            'SELECT coalesce(jsonb_object_agg(id::text, gen_random_uuid()::text), ''{}''::jsonb) FROM public.%I',
            entidade
        ) INTO mapa;
        mapas := jsonb_set(mapas, ARRAY[entidade], mapa);
    END LOOP;

    -- Mantem as mesmas regras de exclusao definidas em 01.sql.
    ALTER TABLE Casa DROP CONSTRAINT FK_Casa_2;
    ALTER TABLE Tarefa DROP CONSTRAINT FK_Tarefa_2;
    ALTER TABLE Tarefa DROP CONSTRAINT FK_Tarefa_3;
    ALTER TABLE Sessao DROP CONSTRAINT FK_Sessao_2;
    ALTER TABLE Pertencer DROP CONSTRAINT FK_Pertencer_1;
    ALTER TABLE Pertencer DROP CONSTRAINT FK_Pertencer_2;
    ALTER TABLE Atribuida DROP CONSTRAINT FK_Atribuida_1;
    ALTER TABLE Atribuida DROP CONSTRAINT FK_Atribuida_2;

    -- Converte primeiro as PKs e depois as FKs com o mesmo mapa.
    FOR coluna IN
        SELECT * FROM (VALUES
            ('usuario', 'id', 'usuario'), ('casa', 'id', 'casa'),
            ('tarefa', 'id', 'tarefa'), ('sessao', 'id', 'sessao'),
            ('casa', 'fk_usuario_id', 'usuario'),
            ('tarefa', 'fk_casa_id', 'casa'),
            ('tarefa', 'fk_usuario_id', 'usuario'),
            ('sessao', 'fk_usuario_id', 'usuario'),
            ('pertencer', 'fk_usuario_id', 'usuario'),
            ('pertencer', 'fk_casa_id', 'casa'),
            ('atribuida', 'fk_usuario_id', 'usuario'),
            ('atribuida', 'fk_tarefa_id', 'tarefa')
        ) AS colunas(tabela, nome, referencia)
    LOOP
        -- Falha em vez de transformar uma referencia sem mapeamento em NULL.
        EXECUTE format(
            'SELECT EXISTS (SELECT 1 FROM public.%I WHERE %I IS NOT NULL AND NOT (%L::jsonb ? %I::text))',
            coluna.tabela, coluna.nome, mapas -> coluna.referencia, coluna.nome
        ) INTO sem_mapeamento;
        IF sem_mapeamento THEN
            RAISE EXCEPTION 'Referencia sem mapeamento em %.%', coluna.tabela, coluna.nome;
        END IF;

        EXECUTE format(
            'ALTER TABLE public.%I ALTER COLUMN %I TYPE UUID USING (%L::jsonb ->> %I::text)::uuid',
            coluna.tabela, coluna.nome, mapas -> coluna.referencia, coluna.nome
        );
        IF coluna.nome = 'id' THEN
            EXECUTE format(
                'ALTER TABLE public.%I ALTER COLUMN id SET DEFAULT gen_random_uuid()',
                coluna.tabela
            );
        END IF;
    END LOOP;

    ALTER TABLE Casa ADD CONSTRAINT FK_Casa_2
        FOREIGN KEY (fk_Usuario_id)
        REFERENCES Usuario (id)
        ON DELETE RESTRICT;

    ALTER TABLE Tarefa ADD CONSTRAINT FK_Tarefa_2
        FOREIGN KEY (fk_Casa_id)
        REFERENCES Casa (id)
        ON DELETE CASCADE;

    ALTER TABLE Tarefa ADD CONSTRAINT FK_Tarefa_3
        FOREIGN KEY (fk_Usuario_id)
        REFERENCES Usuario (id)
        ON DELETE RESTRICT;

    ALTER TABLE Sessao ADD CONSTRAINT FK_Sessao_2
        FOREIGN KEY (fk_Usuario_id)
        REFERENCES Usuario (id)
        ON DELETE CASCADE;

    ALTER TABLE Pertencer ADD CONSTRAINT FK_Pertencer_1
        FOREIGN KEY (fk_Usuario_id)
        REFERENCES Usuario (id)
        ON DELETE RESTRICT;

    ALTER TABLE Pertencer ADD CONSTRAINT FK_Pertencer_2
        FOREIGN KEY (fk_Casa_id)
        REFERENCES Casa (id)
        ON DELETE SET NULL;

    ALTER TABLE Atribuida ADD CONSTRAINT FK_Atribuida_1
        FOREIGN KEY (fk_Usuario_id)
        REFERENCES Usuario (id)
        ON DELETE RESTRICT;

    ALTER TABLE Atribuida ADD CONSTRAINT FK_Atribuida_2
        FOREIGN KEY (fk_Tarefa_id)
        REFERENCES Tarefa (id)
        ON DELETE SET NULL;
END;
$migration$;

COMMIT;
