CREATE TABLE item_compra (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fk_lista_id UUID NOT NULL REFERENCES lista_compra (id) ON DELETE CASCADE,
    nome TEXT NOT NULL CHECK (length(trim(nome)) > 0),
    quantidade INT NOT NULL DEFAULT 1 CHECK (quantidade > 0),
    fk_usuario_criador_id UUID NOT NULL REFERENCES usuario (id) ON DELETE RESTRICT,
    comprado BOOLEAN NOT NULL DEFAULT FALSE,
    fk_usuario_comprador_id UUID REFERENCES usuario (id) ON DELETE SET NULL,
    comprado_em TIMESTAMPTZ,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);