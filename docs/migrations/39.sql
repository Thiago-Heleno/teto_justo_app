CREATE TABLE regra_casa (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_casa_id UUID NOT NULL REFERENCES casa (id) ON DELETE CASCADE,
    titulo TEXT NOT NULL CHECK (length(trim(titulo)) > 0),
    descricao TEXT,
    valor_multa_centavos INT NOT NULL CHECK (valor_multa_centavos > 0),
    ativa BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX regra_casa_fk_casa_id_idx ON regra_casa (fk_casa_id);
