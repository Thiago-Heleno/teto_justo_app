CREATE TABLE lista_compra (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_casa_id UUID NOT NULL REFERENCES casa (id) ON DELETE CASCADE,
    nome TEXT NOT NULL CHECK (length(trim(nome)) > 0),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);