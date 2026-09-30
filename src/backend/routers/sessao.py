from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.security import HTTPAuthorizationCredentials

from core.autenticacao import UsuarioAtual, esquema_bearer
from core.database import get_supabase
from schemas.sessao import LoginEntrada, LoginResposta
from services.sessao import ServicoSessao


router = APIRouter(prefix="/sessoes", tags=["Sessões"])


@router.post("/login", response_model=LoginResposta)
def login(dados: LoginEntrada, resposta: Response, supabase=Depends(get_supabase)):
    sessao = ServicoSessao(supabase).login(dados)
    resposta.headers["Cache-Control"] = "no-store"
    resposta.headers["Pragma"] = "no-cache"
    return sessao


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    usuario_atual: UsuarioAtual,
    credenciais: Annotated[HTTPAuthorizationCredentials, Depends(esquema_bearer)],
    supabase=Depends(get_supabase),
):
    ServicoSessao(supabase).logout(
        credenciais.credentials.strip(), usuario_atual.id
    )
