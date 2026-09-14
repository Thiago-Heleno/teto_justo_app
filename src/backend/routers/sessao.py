from uuid import UUID

from fastapi import APIRouter, Depends, status

from core.database import get_supabase
from schemas.sessao import SessaoAtualizar, SessaoCriar, SessaoResposta
from services.sessao import ServicoSessao


router = APIRouter(prefix="/sessoes", tags=["Sessões"])


@router.post("/", response_model=SessaoResposta, status_code=status.HTTP_201_CREATED)
def criar_sessao(sessao: SessaoCriar, supabase=Depends(get_supabase)):
    return ServicoSessao(supabase).criar_sessao(sessao)


@router.get("/", response_model=list[SessaoResposta])
def listar_sessoes(
    inicio: int = 0,
    limite: int = 100,
    supabase=Depends(get_supabase),
):
    return ServicoSessao(supabase).listar_sessoes(inicio, limite)


@router.get("/{id_sessao}", response_model=SessaoResposta)
def buscar_sessao(id_sessao: UUID, supabase=Depends(get_supabase)):
    return ServicoSessao(supabase).buscar_sessao(id_sessao)


@router.patch("/{id_sessao}", response_model=SessaoResposta)
def atualizar_sessao(
    id_sessao: UUID,
    dados: SessaoAtualizar,
    supabase=Depends(get_supabase),
):
    return ServicoSessao(supabase).atualizar_sessao(id_sessao, dados)


@router.delete("/{id_sessao}", response_model=bool)
def excluir_sessao(id_sessao: UUID, supabase=Depends(get_supabase)):
    return ServicoSessao(supabase).excluir_sessao(id_sessao)
