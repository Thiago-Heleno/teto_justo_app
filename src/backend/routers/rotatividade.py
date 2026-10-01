from fastapi import APIRouter, Depends, status

from core.autenticacao import UsuarioAtual
from core.database import get_supabase
from schemas.rotatividade import RotatividadeCriar, RotatividadeResposta
from services.rotatividade_agendamento import ServicoAgendamentoRotatividade

router = APIRouter(prefix="/rotatividades", tags=["Rotatividade"])


@router.post("/", response_model=RotatividadeResposta, status_code=status.HTTP_201_CREATED)
def criar_rotatividade(
    dados: RotatividadeCriar,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    return ServicoAgendamentoRotatividade(supabase).criar_rotatividade(
        dados,
        usuario_atual.id,
    )
