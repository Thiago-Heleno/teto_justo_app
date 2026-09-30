import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException

from core.database import get_supabase
from schemas.penalidade import ProcessamentoPenalidadesResposta
from schemas.rotatividade import ResultadoJobRotatividade
from services.penalidade import ServicoPenalidade
from services.rotatividade_agendamento import ServicoAgendamentoRotatividade

router = APIRouter(prefix="/jobs", tags=["Jobs internos"])


@router.post(
    "/penalidades",
    response_model=ProcessamentoPenalidadesResposta,
)
def processar_penalidades(
    token: str | None = Header(default=None, alias="X-Penalidade-Job-Token"),
    supabase=Depends(get_supabase),
):
    token_configurado = os.getenv("PENALIDADE_JOB_TOKEN")
    if not token_configurado:
        raise HTTPException(
            status_code=503,
            detail="O processamento agendado de penalidades não está configurado.",
        )
    if token is None or not hmac.compare_digest(
        token_configurado.encode(), token.encode()
    ):
        raise HTTPException(status_code=401, detail="Token de job inválido.")

    return ServicoPenalidade(supabase).processar_tarefas()


@router.post("/rotatividades", response_model=ResultadoJobRotatividade)
def processar_rotatividades(
    token: str | None = Header(default=None, alias="X-Rotatividade-Job-Token"),
    supabase=Depends(get_supabase),
):
    token_configurado = os.getenv("ROTATIVIDADE_JOB_TOKEN")
    if not token_configurado:
        raise HTTPException(
            status_code=503,
            detail="O processamento agendado de rodízios não está configurado.",
        )
    if token is None or not hmac.compare_digest(
        token_configurado.encode(), token.encode()
    ):
        raise HTTPException(status_code=401, detail="Token de job inválido.")

    return ServicoAgendamentoRotatividade(supabase).processar_ocorrencias()
