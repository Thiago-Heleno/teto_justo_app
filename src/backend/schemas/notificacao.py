from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


TokenPush = Annotated[
    str,
    Field(pattern=r"^(?:ExponentPushToken|ExpoPushToken)\[[^\[\]\s]+\]$", repr=False),
]


class DispositivoPushRemover(BaseModel):
    token: TokenPush

    model_config = ConfigDict(extra="forbid")


class DispositivoPushRegistrar(DispositivoPushRemover):
    plataforma: Literal["android", "ios"]


class DispositivoPushResposta(BaseModel):
    id: UUID
    plataforma: Literal["android", "ios"]
    criado_em: datetime


class TicketPush(BaseModel):
    dispositivo_id: UUID
    usuario_id: UUID
    ticket_id: UUID

    model_config = ConfigDict(extra="forbid")


class RecibosPushConsultar(BaseModel):
    tickets: list[TicketPush] = Field(min_length=1, max_length=1000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("tickets")
    @classmethod
    def validar_tickets_unicos(cls, tickets: list[TicketPush]) -> list[TicketPush]:
        if len({ticket.ticket_id for ticket in tickets}) != len(tickets):
            raise ValueError("Os IDs dos tickets devem ser únicos.")
        return tickets
