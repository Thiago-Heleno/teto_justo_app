CREATE INDEX idx_lista_compra_casa ON lista_compra (fk_casa_id);
CREATE INDEX idx_item_compra_lista ON item_compra (fk_lista_id);