from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ListaCompraCriar(BaseModel):
    nome: str = Field(min_length=1)
    fk_casa_id: UUID

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ListaCompraAtualizar(BaseModel):
    nome: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ListaCompraResposta(BaseModel):
    id: UUID
    fk_casa_id: UUID
    nome: str
    criado_em: datetime
