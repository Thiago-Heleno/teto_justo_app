CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. Remove as FKs para muda-las também
ALTER TABLE Casa DROP CONSTRAINT FK_Casa_2;
ALTER TABLE Tarefa DROP CONSTRAINT FK_Tarefa_2;
ALTER TABLE Tarefa DROP CONSTRAINT FK_Tarefa_3;
ALTER TABLE Sessao DROP CONSTRAINT FK_Sessao_2;
ALTER TABLE Pertencer DROP CONSTRAINT FK_Pertencer_1;
ALTER TABLE Pertencer DROP CONSTRAINT FK_Pertencer_2;
ALTER TABLE Atribuida DROP CONSTRAINT FK_Atribuida_1;
ALTER TABLE Atribuida DROP CONSTRAINT FK_Atribuida_2;

-- 2. Converte os ids (PK) para UUID, gerando um valor novo para cada linha existente
ALTER TABLE Casa ALTER COLUMN id TYPE UUID USING gen_random_uuid();
ALTER TABLE Casa ALTER COLUMN id SET DEFAULT gen_random_uuid();

ALTER TABLE Usuario ALTER COLUMN id TYPE UUID USING gen_random_uuid();
ALTER TABLE Usuario ALTER COLUMN id SET DEFAULT gen_random_uuid();

ALTER TABLE Tarefa ALTER COLUMN id TYPE UUID USING gen_random_uuid();
ALTER TABLE Tarefa ALTER COLUMN id SET DEFAULT gen_random_uuid();

ALTER TABLE Sessao ALTER COLUMN id TYPE UUID USING gen_random_uuid();
ALTER TABLE Sessao ALTER COLUMN id SET DEFAULT gen_random_uuid();

-- 3. Converte as colunas de FK para UUID
ALTER TABLE Casa ALTER COLUMN fk_Usuario_id TYPE UUID USING NULL;
ALTER TABLE Tarefa ALTER COLUMN fk_Casa_id TYPE UUID USING NULL;
ALTER TABLE Tarefa ALTER COLUMN fk_Usuario_id TYPE UUID USING NULL;
ALTER TABLE Sessao ALTER COLUMN fk_Usuario_id TYPE UUID USING NULL;
ALTER TABLE Pertencer ALTER COLUMN fk_Usuario_id TYPE UUID USING NULL;
ALTER TABLE Pertencer ALTER COLUMN fk_Casa_id TYPE UUID USING NULL;
ALTER TABLE Atribuida ALTER COLUMN fk_Usuario_id TYPE UUID USING NULL;
ALTER TABLE Atribuida ALTER COLUMN fk_Tarefa_id TYPE UUID USING NULL;

-- 4. Recria as FKs após ter mudado o tipo da váriavel delas
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
