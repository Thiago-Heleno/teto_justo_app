from datetime import datetime
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def validar_timezone(valor: str) -> str:
    try:
        ZoneInfo(valor)
    except (ZoneInfoNotFoundError, ValueError) as erro:
        raise ValueError("Informe um fuso horário IANA válido.") from erro
    return valor


class CasaCriar(BaseModel):
    nome: str
    endereco: str
    foto: Optional[str] = None
    timezone: str = "America/Sao_Paulo"

    @field_validator("timezone")
    @classmethod
    def validar_timezone(cls, valor: str) -> str:
        return validar_timezone(valor)

    model_config = ConfigDict(extra="forbid")


class CasaAtualizar(BaseModel):
    nome: Optional[str] = None
    endereco: Optional[str] = None
    foto: Optional[str] = None
    timezone: Optional[str] = None

    @field_validator("timezone")
    @classmethod
    def validar_timezone(cls, valor: str | None) -> str | None:
        if valor is not None:
            validar_timezone(valor)
        return valor

    model_config = ConfigDict(extra="forbid")


class CasaResposta(BaseModel):
    id: UUID
    nome: str
    endereco: str
    foto: Optional[str] = None
    fk_usuario_id: UUID
    timezone: str

class EntrarCasaPedido(BaseModel):
    convite: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class CasaConviteResposta(BaseModel):
    convite: str
    expira_em: datetime


class ErroCasaResposta(BaseModel):
    detail: str


class MoradorResposta(BaseModel):
    id: UUID
    nome: str
    email: EmailStr
    telefone: Optional[int] = None
    foto: Optional[str] = None
    score: int


class MoradorPlacarResposta(BaseModel):
    usuario_id: UUID
    nome: str
    semanal: int
    mensal: int
    anual: int
    acumulado: int


class CasaPlacarResposta(BaseModel):
    casa_id: UUID
    fuso_horario: str
    moradores: list[MoradorPlacarResposta]


class DivergenciaScoreResposta(BaseModel):
    usuario_id: UUID
    saldo_materializado: int | None
    acumulado_eventos: int
    diferenca: int | None


class AuditoriaScoreResposta(BaseModel):
    casa_id: UUID
    divergencias: list[DivergenciaScoreResposta]
