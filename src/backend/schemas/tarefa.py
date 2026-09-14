from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TarefaCriar(BaseModel):
    nome: str
    descricao: Optional[str] = None
    estado_atual: int
    data_fim: datetime
    fk_casa_id: UUID
    usuarios_atribuidos: Optional[list[UUID]] = None
    fk_usuario_id: UUID


class TarefaAtualizar(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    estado_atual: Optional[int] = None
    data_fim: Optional[datetime] = None
    fk_casa_id: Optional[UUID] = None
    usuarios_atribuidos: Optional[list[UUID]] = None


class TarefaResposta(BaseModel):
    id: UUID
    nome: str
    descricao: Optional[str] = None
    estado_atual: int
    data_fim: datetime
    fk_casa_id: UUID
    usuarios_atribuidos: list[UUID] = Field(default_factory=list)
    fk_usuario_id: UUID
