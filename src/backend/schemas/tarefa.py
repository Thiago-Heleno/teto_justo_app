from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


EstadoTarefa = Literal["pendente", "atrasada", "finalizado", "nao_feito"]


class TarefaCriar(BaseModel):
    nome: str
    descricao: Optional[str] = None
    estado_atual: EstadoTarefa
    data_fim: datetime
    fk_casa_id: UUID
    usuarios_atribuidos: Optional[list[UUID]] = None
    fk_usuario_id: UUID


class TarefaAtualizar(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    estado_atual: Optional[EstadoTarefa] = None
    data_fim: Optional[datetime] = None
    usuarios_atribuidos: Optional[list[UUID]] = None

    model_config = ConfigDict(extra="forbid")


class TarefaResposta(BaseModel):
    id: UUID
    nome: str
    descricao: Optional[str] = None
    estado_atual: EstadoTarefa
    data_fim: datetime
    fk_casa_id: UUID
    usuarios_atribuidos: list[UUID] = Field(default_factory=list)
    fk_usuario_id: UUID
