from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import origens_frontend
from core.database import get_supabase
from schemas.usuario import UsuarioResposta
from services.sessao import ServicoSessao


esquema_bearer = HTTPBearer(auto_error=False)
COOKIE_SESSAO = "teto_justo_session"


def _erro_nao_autenticado() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não autenticado.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def obter_usuario_atual(
    request: Request,
    credenciais: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(esquema_bearer),
    ],
    supabase=Depends(get_supabase),
) -> UsuarioResposta:
    token = (
        credenciais.credentials.strip()
        if credenciais and credenciais.scheme.lower() == "bearer"
        else request.cookies.get(COOKIE_SESSAO, "").strip()
    )
    if not token:
        raise _erro_nao_autenticado()

    usa_cookie = not (credenciais and credenciais.scheme.lower() == "bearer")
    if usa_cookie:
        origem = request.headers.get("origin", "").rstrip("/")
        if origem not in origens_frontend():
            raise HTTPException(status_code=403, detail="Origem não autorizada.")

    usuario = ServicoSessao(supabase).obter_usuario_por_token(token)
    if usuario is None:
        raise _erro_nao_autenticado()
    return usuario


UsuarioAtual = Annotated[UsuarioResposta, Depends(obter_usuario_atual)]
