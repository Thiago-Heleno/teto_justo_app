from uuid import UUID

from fastapi import APIRouter, Depends

from core.autenticacao import UsuarioAtual
from core.database import get_supabase
from schemas.rotatividade import RotatividadeCriar, RotatividadeResposta
from schemas.tarefa import TarefaResposta
from services.rotatividade import ServicoRotatividade

router = APIRouter(prefix="/rotatividades", tags=["Rotatividades"])


@router.post("/", response_model=RotatividadeResposta, status_code=201)
def criar_rotatividade(
    dados: RotatividadeCriar,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    return ServicoRotatividade(supabase).criar(dados, usuario_atual.id)


@router.get("/{id_rotatividade}/ocorrencias", response_model=list[TarefaResposta])
def listar_ocorrencias(
    id_rotatividade: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    return ServicoRotatividade(supabase).listar_ocorrencias(
        id_rotatividade, usuario_atual.id
    )
