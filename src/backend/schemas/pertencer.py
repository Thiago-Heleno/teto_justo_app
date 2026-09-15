from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PertencerCriar(BaseModel):
    fk_usuario_id: UUID
    fk_casa_id: UUID
    score: int = 0


class PertencerAtualizar(BaseModel):
    score: int


class PertencerResposta(BaseModel):
    fk_usuario_id: UUID
    fk_casa_id: UUID
    score: int

    model_config = ConfigDict(from_attributes=True)
