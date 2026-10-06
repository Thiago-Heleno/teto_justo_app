import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials

from core.autenticacao import COOKIE_SESSAO, UsuarioAtual, esquema_bearer
from core.config import origens_frontend
from core.database import get_supabase
from schemas.sessao import LoginEntrada, LoginResposta
from services.sessao import ServicoSessao


router = APIRouter(prefix="/sessoes", tags=["Sessões"])


@router.post("/login", response_model=LoginResposta)
def login(
    dados: LoginEntrada,
    request: Request,
    resposta: Response,
    supabase=Depends(get_supabase),
):
    usa_cookie = request.headers.get("x-session-transport") == "cookie"
    if usa_cookie:
        origem = request.headers.get("origin", "").rstrip("/")
        if origem not in origens_frontend():
            raise HTTPException(status_code=403, detail="Origem não autorizada.")

    sessao = ServicoSessao(supabase).login(dados)
    resposta.headers["Cache-Control"] = "no-store"
    resposta.headers["Pragma"] = "no-cache"
    if usa_cookie:
        secure = os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"
        resposta.set_cookie(
            key=COOKIE_SESSAO,
            value=sessao.token,
            max_age=24 * 60 * 60,
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/",
        )
        sessao.token = None
    return sessao


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    resposta: Response,
    usuario_atual: UsuarioAtual,
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(esquema_bearer)],
    supabase=Depends(get_supabase),
):
    token = (
        credenciais.credentials.strip()
        if credenciais
        else request.cookies.get(COOKIE_SESSAO, "")
    )
    ServicoSessao(supabase).logout(token, usuario_atual.id)
    secure = os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"
    resposta.delete_cookie(
        key=COOKIE_SESSAO,
        path="/",
        httponly=True,
        secure=secure,
        samesite="lax",
    )
