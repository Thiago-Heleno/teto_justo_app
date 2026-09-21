from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


EstadoTarefa = Literal["pendente", "atrasada", "finalizado", "nao_feito"]


class TarefaCriar(BaseModel):
    nome: str
    descricao: Optional[str] = None
    estado_atual: EstadoTarefa
    data_fim: datetime
    fk_casa_id: UUID
    usuarios_atribuidos: list[UUID] = Field(min_length=1)
    fk_usuario_id: UUID
    peso: int = Field(gt=0, le=4)

    model_config = ConfigDict(extra="forbid")

    @field_validator("data_fim")
    @classmethod
    def validar_prazo_futuro(cls, valor: datetime) -> datetime:
        prazo = valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
        if prazo <= datetime.now(timezone.utc):
            raise ValueError("O prazo deve estar no futuro.")
        return valor


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
