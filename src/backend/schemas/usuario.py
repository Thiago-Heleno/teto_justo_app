from pydantic import BaseModel, EmailStr, field_validator, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class UsuarioCriar(BaseModel):
    nome: str
    email: EmailStr
    telefone: Optional[int] = None
    senha: str
    foto: Optional[str] = None
    usuario_tipo: Optional[int] = 0

    @field_validator("senha")
    @classmethod
    def validar_senha(cls, senha: str) -> str:
        if not senha:
            raise ValueError("A senha não pode estar vazia.")
        if len(senha.encode("utf-8")) > 72:
            raise ValueError("A senha deve ter no máximo 72 bytes.")
        return senha


class UsuarioAtualizar(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[int] = None
    foto: Optional[str] = None


class UsuarioResposta(BaseModel):
    id: UUID  # VOLTOU PARA UUID
    nome: str
    email: EmailStr
    telefone: Optional[int] = None
    foto: Optional[str] = None
    usuario_tipo: Optional[int] = None
    data_criacao: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
