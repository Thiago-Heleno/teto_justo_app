from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator

class UsuarioCriar(BaseModel):
    nome: str
    email: EmailStr
    telefone: Optional[str] = None
    senha: str
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
    telefone: Optional[str] = None


class UsuarioResposta(BaseModel):
    id: UUID
    nome: str
    email: EmailStr