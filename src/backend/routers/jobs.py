import hmac
import os

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Response

from core.database import get_supabase
from schemas.notificacao import RecibosPushConsultar
from schemas.penalidade import ProcessamentoPenalidadesResposta
from schemas.rotatividade import ResultadoJobRotatividade
from services.penalidade import ServicoPenalidade
from services.notificacao import ServicoNotificacao
from services.rotatividade_agendamento import ServicoAgendamentoRotatividade

router = APIRouter(prefix="/jobs", tags=["Jobs internos"])


def validar_cron(
    response: Response,
    authorization: str | None = Header(default=None),
) -> None:
    segredo = os.getenv("CRON_SECRET")
    if not segredo:
        raise HTTPException(status_code=503, detail="O agendamento da Vercel não está configurado.")
    if authorization is None or not hmac.compare_digest(
        authorization.encode(), f"Bearer {segredo}".encode()
    ):
        raise HTTPException(status_code=401, detail="Token de job inválido.")
    response.headers["Cache-Control"] = "no-store"


@router.get(
    "/penalidades",
    response_model=ProcessamentoPenalidadesResposta,
    dependencies=[Depends(validar_cron)],
)
def processar_penalidades_cron(tarefas_fundo: BackgroundTasks, supabase=Depends(get_supabase)):
    return ServicoPenalidade(supabase, tarefas_fundo).processar_tarefas()


@router.get(
    "/rotatividades",
    response_model=ResultadoJobRotatividade,
    dependencies=[Depends(validar_cron)],
)
def processar_rotatividades_cron(supabase=Depends(get_supabase)):
    return ServicoAgendamentoRotatividade(supabase).processar_ocorrencias()


@router.get("/notificacoes", dependencies=[Depends(validar_cron)])
def processar_notificacoes_cron(supabase=Depends(get_supabase)):
    return ServicoNotificacao(supabase).avisar_vencimentos()


@router.get("/notificacoes-avisos", dependencies=[Depends(validar_cron)])
def processar_avisos_inicio_cron(supabase=Depends(get_supabase)):
    return ServicoNotificacao(supabase).avisar_inicios()


@router.post("/notificacoes-recibos", dependencies=[Depends(validar_cron)])
def consultar_recibos_notificacoes(
    dados: RecibosPushConsultar, supabase=Depends(get_supabase)
):
    return ServicoNotificacao(supabase).consultar_recibos(dados.tickets)


@router.post(
    "/penalidades",
    response_model=ProcessamentoPenalidadesResposta,
)
def processar_penalidades(
    tarefas_fundo: BackgroundTasks,
    token: str | None = Header(default=None, alias="X-Penalidade-Job-Token"),
    supabase=Depends(get_supabase),
):
    token_configurado = os.getenv("PENALIDADE_JOB_TOKEN")
    if not token_configurado:
        raise HTTPException(
            status_code=503,
            detail="O processamento agendado de penalidades não está configurado.",
        )
    if token is None or not hmac.compare_digest(token_configurado.encode(), token.encode()):
        raise HTTPException(status_code=401, detail="Token de job inválido.")

    return ServicoPenalidade(supabase, tarefas_fundo).processar_tarefas()


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
    if token is None or not hmac.compare_digest(token_configurado.encode(), token.encode()):
        raise HTTPException(status_code=401, detail="Token de job inválido.")

    return ServicoAgendamentoRotatividade(supabase).processar_ocorrencias()
