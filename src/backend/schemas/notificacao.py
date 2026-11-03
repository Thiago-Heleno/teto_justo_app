from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TokenPush = Annotated[
    str,
    Field(pattern=r"^(?:ExponentPushToken|ExpoPushToken)\[[^\[\]\s]+\]$", repr=False),
]
TokenWeb = Annotated[str, Field(min_length=1, max_length=2048, repr=False)]


class DispositivoPushRemover(BaseModel):
    token: str | None = Field(default=None, min_length=1, max_length=2048)
    endpoint: str | None = Field(default=None, min_length=1, max_length=2048)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validar_identificador(self):
        if not self.token and not self.endpoint:
            raise ValueError("Informe o token ou endpoint do dispositivo.")
        return self


class DispositivoPushRegistrar(DispositivoPushRemover):
    plataforma: Literal["android", "ios", "web"]
    @field_validator("token")
    @classmethod
    def validar_token_expo(cls, token: str | None, info) -> str | None:
        return token

    @model_validator(mode="after")
    def validar_token(self):
        if self.plataforma in {"android", "ios"} and (
            not self.token
            or not self.token.startswith(("ExpoPushToken[", "ExponentPushToken["))
            or " " in self.token
            or self.token.endswith("[]")
        ):
            raise ValueError("Token Expo inválido.")
        if self.plataforma == "web" and not self.token:
            raise ValueError("O token FCM web é obrigatório.")
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
