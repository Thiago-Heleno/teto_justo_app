from uuid import UUID
from typing import Literal

from pydantic import BaseModel, ConfigDict


class PertencerCriar(BaseModel):
    fk_usuario_id: UUID
    fk_casa_id: UUID
    score: Literal[0] = 0

    model_config = ConfigDict(extra="forbid")


class PertencerResposta(BaseModel):
    fk_usuario_id: UUID
    fk_casa_id: UUID
    score: int

    model_config = ConfigDict(from_attributes=True)
