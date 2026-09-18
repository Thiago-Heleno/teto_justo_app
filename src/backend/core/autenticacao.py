from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.database import get_supabase
from schemas.usuario import UsuarioResposta
from services.sessao import ServicoSessao


esquema_bearer = HTTPBearer(auto_error=False)


def _erro_nao_autenticado() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def obter_usuario_atual(
    credenciais: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(esquema_bearer),
    ],
    supabase=Depends(get_supabase),
) -> UsuarioResposta:
    if (
        credenciais is None
        or credenciais.scheme.lower() != "bearer"
        or not credenciais.credentials.strip()
    ):
        raise _erro_nao_autenticado()

    usuario = ServicoSessao(supabase).obter_usuario_por_token(
        credenciais.credentials.strip()
    )
    if usuario is None:
        raise _erro_nao_autenticado()
    return usuario


UsuarioAtual = Annotated[UsuarioResposta, Depends(obter_usuario_atual)]
