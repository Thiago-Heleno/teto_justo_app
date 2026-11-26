-- fk_regra_id sem CASCADE: regra com multa não é apagada, mas excluir a casa ainda apaga as duas.
CREATE TABLE multa_casa (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_casa_id UUID NOT NULL REFERENCES casa (id) ON DELETE CASCADE,
    fk_regra_id UUID NOT NULL REFERENCES regra_casa (id),
    titulo_regra TEXT NOT NULL,
    fk_usuario_multado_id UUID NOT NULL REFERENCES usuario (id) ON DELETE RESTRICT,
    fk_usuario_aplicador_id UUID NOT NULL REFERENCES usuario (id) ON DELETE RESTRICT,
    valor_centavos INT NOT NULL CHECK (valor_centavos > 0),
    observacao TEXT,
    paga BOOLEAN NOT NULL DEFAULT FALSE,
    pago_em TIMESTAMPTZ,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (paga = (pago_em IS NOT NULL))
);

CREATE INDEX multa_casa_fk_casa_id_idx ON multa_casa (fk_casa_id);
CREATE INDEX multa_casa_fk_regra_id_idx ON multa_casa (fk_regra_id);
