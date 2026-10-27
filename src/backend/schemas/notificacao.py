from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class NotificacaoTesteEntrada(BaseModel):
    tipo: Literal["tarefa_atribuida", "tarefa_vence_hoje", "tarefa_atrasada"]
    tarefa_id: UUID

    model_config = ConfigDict(extra="forbid")


class NotificacaoTesteResposta(BaseModel):
    aceitos: int
    falhas: int
    invalidos: int
