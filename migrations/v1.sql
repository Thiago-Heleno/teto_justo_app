CREATE TABLE Casa (
    id INT PRIMARY KEY,
    endereco VARCHAR,
    nome VARCHAR,
    foto BYTEA,
    fk_Usuario_id INT
);

CREATE TABLE Usuario (
    id INT PRIMARY KEY,
    nome VARCHAR,
    telefone BIGINT, -- Changed to BIGINT in case phone numbers exceed standard INT limits
    email VARCHAR,
    senha_hash VARCHAR,
    data_criacao TIMESTAMP,
    foto BYTEA,
    Usuario_TIPO INT
);

CREATE TABLE Tarefa (
    id INT PRIMARY KEY,
    criado_em TIMESTAMP,
    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,
    pontuacao INT,
    descricao VARCHAR,
    nome VARCHAR,
    estado_atual INT,
    fk_Casa_id INT,
    fk_Usuario_id INT
);

CREATE TABLE Sessao (
    id INT PRIMARY KEY,
    token VARCHAR,
    criado_em TIMESTAMP,
    expira_em TIMESTAMP,
    fk_Usuario_id INT
);

CREATE TABLE Pertencer (
    fk_Usuario_id INT,
    fk_Casa_id INT,
    Score INT
);

CREATE TABLE Atribuida (
    fk_Usuario_id INT,
    fk_Tarefa_id INT
);
 
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