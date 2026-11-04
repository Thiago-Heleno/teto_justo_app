import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_TOKEN_EXPO = re.compile(r"(?:ExponentPushToken|ExpoPushToken)\[[^\[\]\s]+\]")


class DispositivoPushRemover(BaseModel):
    token: str = Field(min_length=1, max_length=2048, repr=False)

    model_config = ConfigDict(extra="forbid")


class DispositivoPushRegistrar(DispositivoPushRemover):
    plataforma: Literal["android", "ios", "web"]

    @model_validator(mode="after")
    def validar_token(self):
        # Tokens web são tokens FCM, sem formato fixo; os demais são tokens Expo.
        if self.plataforma != "web" and not _TOKEN_EXPO.fullmatch(self.token):
            raise ValueError("Token Expo inválido.")
        return self


class DispositivoPushResposta(BaseModel):
    id: UUID
    plataforma: Literal["android", "ios", "web"]
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
