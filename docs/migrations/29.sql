BEGIN;

CREATE TABLE dispositivo_push (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_usuario_id UUID NOT NULL REFERENCES usuario (id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE CHECK (length(trim(token)) > 0),
    plataforma TEXT NOT NULL CHECK (plataforma IN ('android', 'ios')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dispositivo_push_usuario ON dispositivo_push (fk_usuario_id);

REVOKE ALL ON dispositivo_push FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON dispositivo_push TO service_role;

COMMIT;
