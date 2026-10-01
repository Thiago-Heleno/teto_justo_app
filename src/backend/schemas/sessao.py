from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr


class LoginEntrada(BaseModel):
    email: EmailStr
    senha: SecretStr = Field(min_length=1, max_length=72)

    model_config = ConfigDict(extra="forbid")


class LoginResposta(BaseModel):
    token: str
    expira_em: datetime
