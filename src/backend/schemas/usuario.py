from pydantic import BaseModel, EmailStr
from typing import Optional


class UsuarioCriar(BaseModel):
    nome: str
    email: EmailStr
    telefone: Optional[str] = None
    senha: str


class UsuarioAtualizar(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None


class UsuarioResposta(BaseModel):
    id: str
    nome: str
    email: EmailStr
