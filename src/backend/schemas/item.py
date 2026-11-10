from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ItemCompraCriar(BaseModel):
    nome: str = Field(min_length=1)
    quantidade: int = Field(default=1, strict=True, gt=0)
    fk_lista_id: UUID

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ItemCompraAtualizar(BaseModel):
    nome: str | None = Field(default=None, min_length=1)
    quantidade: int | None = Field(default=None, strict=True, gt=0)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def rejeitar_nulos(self):
        for campo in self.model_fields_set:
            if getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo.")
        return self


class ItemCompraResposta(BaseModel):
    id: UUID
    fk_lista_id: UUID
    nome: str
    quantidade: int
    fk_usuario_criador_id: UUID
    comprado: bool
    fk_usuario_comprador_id: UUID | None = None
    comprado_em: datetime | None = None
    criado_em: datetime
