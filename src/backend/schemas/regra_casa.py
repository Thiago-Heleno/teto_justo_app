from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ValorCentavos = Annotated[int, Field(gt=0, le=2147483647)]


class RegraCasaCriar(BaseModel):
    fk_casa_id: UUID
    titulo: str = Field(min_length=1)
    descricao: str | None = None
    valor_multa_centavos: ValorCentavos

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("descricao")
    @classmethod
    def descricao_vazia_vira_nula(cls, valor):
        return valor or None


class RegraCasaAtualizar(BaseModel):
    titulo: str | None = Field(default=None, min_length=1)
    descricao: str | None = None
    valor_multa_centavos: ValorCentavos | None = None
    ativa: bool | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("descricao")
    @classmethod
    def descricao_vazia_vira_nula(cls, valor):
        return valor or None

    @field_validator("titulo", "valor_multa_centavos", "ativa")
    @classmethod
    def nao_aceita_nulo(cls, valor):
        if valor is None:
            raise ValueError("Valor não pode ser nulo.")
        return valor


class MultaCasaCriar(BaseModel):
    fk_casa_id: UUID
    fk_regra_id: UUID
    fk_usuario_multado_id: UUID
    observacao: str | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("observacao")
    @classmethod
    def observacao_vazia_vira_nula(cls, valor):
        return valor or None


class MultaCasaResposta(BaseModel):
    id: UUID
    fk_casa_id: UUID
    fk_regra_id: UUID
    titulo_regra: str
    fk_usuario_multado_id: UUID
    fk_usuario_aplicador_id: UUID
    valor_centavos: int
    observacao: str | None
    paga: bool
    pago_em: datetime | None
    criado_em: datetime


class RegraCasaResposta(BaseModel):
    id: UUID
    fk_casa_id: UUID
    titulo: str
    descricao: str | None
    valor_multa_centavos: int
    ativa: bool
    criado_em: datetime
