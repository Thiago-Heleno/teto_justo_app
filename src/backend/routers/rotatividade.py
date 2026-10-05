from uuid import UUID

from fastapi import APIRouter, Depends, status

from core.autenticacao import UsuarioAtual
from core.database import get_supabase
from schemas.rotatividade import (
    RotatividadeAtualizar,
    RotatividadeCriar,
    RotatividadeDetalhe,
    RotatividadeResposta,
)
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


@router.get("/", response_model=list[RotatividadeDetalhe])
def listar_rotatividades(
    fk_casa_id: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    return ServicoAgendamentoRotatividade(supabase).listar_rotatividades(
        fk_casa_id,
        usuario_atual.id,
    )


@router.patch("/{id_rotatividade}", response_model=RotatividadeDetalhe)
def atualizar_rotatividade(
    id_rotatividade: UUID,
    dados: RotatividadeAtualizar,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    return ServicoAgendamentoRotatividade(supabase).atualizar_rotatividade(
        id_rotatividade,
        dados,
        usuario_atual.id,
    )


@router.delete("/{id_rotatividade}", response_model=bool)
def excluir_rotatividade(
    id_rotatividade: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    return ServicoAgendamentoRotatividade(supabase).excluir_rotatividade(
        id_rotatividade,
        usuario_atual.id,
    )
