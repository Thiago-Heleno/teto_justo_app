from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SessaoCriar(BaseModel):
    token: str = Field(min_length=1)
    expira_em: datetime
    fk_usuario_id: UUID


class SessaoAtualizar(BaseModel):
    token: Optional[str] = Field(default=None, min_length=1)
    expira_em: Optional[datetime] = None


class SessaoResposta(BaseModel):
    id: UUID
    token: str
    criado_em: Optional[datetime] = None
    expira_em: datetime
    fk_usuario_id: UUID

    model_config = ConfigDict(from_attributes=True)
