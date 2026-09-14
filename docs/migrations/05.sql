-- Adiciona chave primaria composta nas tabelas de associacao, impedindo duplicatas
-- (um usuario nao pode pertencer duas vezes a mesma casa, nem ser atribuido duas
-- vezes a mesma tarefa).

BEGIN;

ALTER TABLE Pertencer ADD CONSTRAINT PK_Pertencer PRIMARY KEY (fk_Usuario_id, fk_Casa_id);
ALTER TABLE Atribuida ADD CONSTRAINT PK_Atribuida PRIMARY KEY (fk_Usuario_id, fk_Tarefa_id);

-- As colunas da PK agora sao NOT NULL, entao "ON DELETE SET NULL" nao e mais valido
-- nessas FKs. Troca para CASCADE: apagar a casa/tarefa remove o vinculo junto.

ALTER TABLE Pertencer DROP CONSTRAINT FK_Pertencer_2;
ALTER TABLE Pertencer ADD CONSTRAINT FK_Pertencer_2
    FOREIGN KEY (fk_Casa_id)
    REFERENCES Casa (id)
    ON DELETE CASCADE;

ALTER TABLE Atribuida DROP CONSTRAINT FK_Atribuida_2;
ALTER TABLE Atribuida ADD CONSTRAINT FK_Atribuida_2
    FOREIGN KEY (fk_Tarefa_id)
    REFERENCES Tarefa (id)
    ON DELETE CASCADE;

COMMIT;


