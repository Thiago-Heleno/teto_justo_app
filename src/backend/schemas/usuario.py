from base64 import b64encode
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict, PlainSerializer
from typing import Annotated, Optional
from uuid import UUID
from datetime import datetime


def _serializar_foto_perfil(foto: str) -> str | None:
    if not foto.startswith("\\x"):
        return foto
    try:
        conteudo = bytes.fromhex(foto[2:])
    except ValueError:
        return None
    # O cadastro e o PATCH antigos também aceitam Base64 como texto na coluna binária.
    if conteudo.isascii() and (texto := conteudo.decode("ascii")).isprintable():
        return texto
    return b64encode(conteudo).decode("ascii")


FotoPerfilResposta = Annotated[str, PlainSerializer(_serializar_foto_perfil, when_used="json")]


def _validar_senha(senha: str) -> str:
    if not senha:
        raise ValueError("A senha não pode estar vazia.")
    if len(senha.encode("utf-8")) > 72:
        raise ValueError("A senha deve ter no máximo 72 bytes.")
    return senha


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
        return _validar_senha(senha)


class UsuarioCadastro(UsuarioCriar):
    codigo: str = Field(pattern=r"^\d{5}$")
    token_verificacao: str


class VerificacaoEmailResposta(BaseModel):
    token_verificacao: str
    expira_em: datetime


class RecuperarSenhaEntrada(BaseModel):
    email: EmailStr


class RedefinirSenhaEntrada(BaseModel):
    email: EmailStr
    codigo: str = Field(pattern=r"^\d{5}$")
    token_verificacao: str
    nova_senha: str

    @field_validator("nova_senha")
    @classmethod
    def validar_nova_senha(cls, senha: str) -> str:
        return _validar_senha(senha)


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
    foto: Optional[FotoPerfilResposta] = None
    usuario_tipo: Optional[int] = None
    data_criacao: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
