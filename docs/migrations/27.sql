BEGIN;

-- Novos vínculos começam com saldo zero mesmo fora da API.
ALTER TABLE pertencer ALTER COLUMN score SET DEFAULT 0;

-- A saída preserva o vínculo, o saldo e os eventos. Vínculos existentes seguem ativos.
ALTER TABLE pertencer ADD COLUMN ativo BOOLEAN NOT NULL DEFAULT TRUE;

-- A PK começa por usuário; listas de moradores buscam os ativos por casa.
CREATE INDEX idx_pertencer_casa_usuario
    ON pertencer (fk_casa_id, fk_usuario_id) WHERE ativo;

-- A FK abaixo consulta os eventos pelo par usuário/casa.
CREATE INDEX idx_score_event_usuario_casa
    ON score_event (fk_usuario_id, fk_casa_id);

-- Eventos exigem o vínculo que guarda o saldo, mesmo após a saída.
-- Antes de aplicar, verificar eventos sem vínculo (ver revisão da sprint 2).
ALTER TABLE score_event ADD CONSTRAINT fk_scoreevent_pertencer
    FOREIGN KEY (fk_usuario_id, fk_casa_id)
    REFERENCES pertencer (fk_usuario_id, fk_casa_id)
    ON DELETE RESTRICT;

COMMIT;
