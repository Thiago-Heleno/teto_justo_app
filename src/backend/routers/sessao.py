from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials

from core.autenticacao import UsuarioAtual, esquema_bearer
from core.database import get_supabase
from schemas.sessao import LoginEntrada, LoginResposta
from services.sessao import ServicoSessao
from services.limite_login import LimitadorLogin, get_limitador_login


router = APIRouter(prefix="/sessoes", tags=["Sessões"])


@router.post(
    "/login",
    response_model=LoginResposta,
    responses={
        429: {
            "description": "Limite temporário de tentativas de login.",
            "headers": {
                "Retry-After": {
                    "description": "Segundos restantes até nova tentativa.",
                    "schema": {"type": "integer"},
                }
            },
        },
        503: {"description": "Serviço de limitação de login indisponível."},
    },
)
def login(
    dados: LoginEntrada,
    resposta: Response,
    request: Request,
    supabase=Depends(get_supabase),
    limitador: LimitadorLogin = Depends(get_limitador_login),
):
    ip = request.client.host if request.client else None
    if not ip:
        raise HTTPException(status_code=503, detail="Login temporariamente indisponível.")
    email = str(dados.email)
    limitador.reservar_tentativa(email, ip)
    sucesso_confirmado = False

    def confirmar_sucesso() -> None:
        nonlocal sucesso_confirmado
        limitador.confirmar_sucesso(email, ip)
        sucesso_confirmado = True

    try:
        sessao = ServicoSessao(supabase).login(
            dados, antes_de_emitir_token=confirmar_sucesso
        )
    except HTTPException as erro:
        if erro.status_code == 401:
            limitador.registrar_falha(email, ip)
        elif not sucesso_confirmado:
            limitador.cancelar_tentativa(email, ip)
        raise
    except Exception:
        if not sucesso_confirmado:
            limitador.cancelar_tentativa(email, ip)
        raise
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
