from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


EstadoTarefa = Literal["pendente", "atrasada", "finalizado", "nao_feito"]


PontuacaoTarefa = Literal[10, 20, 30, 40]


class TarefaCriar(BaseModel):
    nome: str
    descricao: Optional[str] = None
    estado_atual: EstadoTarefa
    peso: Literal[1, 2, 3, 4]
    pontuacao: PontuacaoTarefa
    atraso_maximo: int = Field(gt=0)
    data_fim: datetime
    fk_casa_id: UUID
    usuarios_atribuidos: Optional[list[UUID]] = None
    fk_usuario_id: UUID


class TarefaAtualizar(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    estado_atual: Optional[EstadoTarefa] = None
    peso: Optional[Literal[1, 2, 3, 4]] = None
    pontuacao: Optional[PontuacaoTarefa] = None
    atraso_maximo: Optional[int] = Field(default=None, gt=0)
    data_fim: Optional[datetime] = None
    usuarios_atribuidos: Optional[list[UUID]] = None

    model_config = ConfigDict(extra="forbid")


class TarefaResposta(BaseModel):
    id: UUID
    nome: str
    descricao: Optional[str] = None
    estado_atual: EstadoTarefa
    peso: int
    pontuacao: int
    atraso_maximo: int
    data_fim: datetime
    fk_casa_id: UUID
    usuarios_atribuidos: list[UUID] = Field(default_factory=list)
    fk_usuario_id: UUID
