from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CasaCriar(BaseModel):
    nome: str
    endereco: str
    foto: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class CasaAtualizar(BaseModel):
    nome: Optional[str] = None
    endereco: Optional[str] = None
    foto: Optional[str] = None


class CasaResposta(BaseModel):
    id: UUID
    nome: str
    endereco: str
    foto: Optional[str] = None
    fk_usuario_id: UUID
