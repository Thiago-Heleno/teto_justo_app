from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from schemas.tarefa import AtrasoMaximo, ModoPrazo, PesoTarefa, PrazoDias


DiaSemana = Annotated[int, Field(strict=True, ge=1, le=7)]


class RotatividadeCriar(BaseModel):
    fk_casa_id: UUID
    nome: str = Field(min_length=1)
    descricao: str | None = None
    peso: PesoTarefa
    prazo_dias: PrazoDias
    atraso_maximo: AtrasoMaximo
    modo_prazo: ModoPrazo
    participantes: list[UUID] = Field(min_length=2)
    dias_semana: list[DiaSemana] = Field(min_length=1, max_length=7)
    intervalo_semanas: Annotated[int, Field(strict=True, ge=1, le=4)] = 1

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("participantes")
    @classmethod
    def participantes_distintos(cls, participantes: list[UUID]) -> list[UUID]:
        if len(set(participantes)) != len(participantes):
            raise ValueError("Os participantes devem ser diferentes.")
        return participantes

    @field_validator("dias_semana")
    @classmethod
    def dias_distintos(cls, dias: list[int]) -> list[int]:
        if len(set(dias)) != len(dias):
            raise ValueError("Os dias da semana devem ser diferentes.")
        return dias


class RotatividadeResposta(RotatividadeCriar):
    id: UUID
    pontuacao: int
    semana_ancora: str
    ativa: bool
    criado_em: str
