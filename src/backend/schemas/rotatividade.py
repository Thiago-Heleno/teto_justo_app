from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


PesoRotatividade = Annotated[int, Field(strict=True, ge=1, le=3)]
PrazoRotatividade = Annotated[int, Field(strict=True, ge=1, le=5)]
DiaSemanaRotatividade = Annotated[int, Field(strict=True, ge=1, le=7)]
IntervaloRotatividade = Annotated[int, Field(strict=True, ge=1, le=4)]


class RotatividadeCriar(BaseModel):
    fk_casa_id: UUID
    nome: str = Field(min_length=1)
    descricao: str | None = None
    peso: PesoRotatividade
    prazo_dias: PrazoRotatividade
    atraso_maximo: PrazoRotatividade
    modo_prazo: Literal["dia_fixo", "intervalo"] = "intervalo"
    participantes: list[UUID] = Field(min_length=2)
    dias_semana: list[DiaSemanaRotatividade] = Field(min_length=1, max_length=7)
    intervalo_semanas: IntervaloRotatividade

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("participantes")
    @classmethod
    def validar_participantes_unicos(cls, valor: list[UUID]) -> list[UUID]:
        if len(set(valor)) != len(valor):
            raise ValueError("Os participantes devem ser pessoas diferentes.")
        return valor

    @field_validator("dias_semana")
    @classmethod
    def validar_dias_unicos(cls, valor: list[int]) -> list[int]:
        if len(set(valor)) != len(valor):
            raise ValueError("Os dias da semana não podem se repetir.")
        return sorted(valor)

    @field_validator("nome")
    @classmethod
    def validar_nome_nao_vazio(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("Informe o nome da tarefa.")
        return valor


class RotatividadeResposta(BaseModel):
    id: UUID
    fk_casa_id: UUID
    nome: str
    ativa: bool


class ResultadoJobRotatividade(BaseModel):
    rotatividades_analisadas: int
    ocorrencias_processadas: int
