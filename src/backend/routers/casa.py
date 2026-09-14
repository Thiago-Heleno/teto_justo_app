from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from core.database import get_supabase
from schemas.casa import CasaAtualizar, CasaCriar, CasaResposta

router = APIRouter(prefix="/casas", tags=["Casas"])


def _obter_servico_casa(supabase):
    try:
        from services.casa import ServicoCasa
    except ModuleNotFoundError as erro:
        if erro.name != "services.casa":
            raise

        raise HTTPException(
            status_code=501,
            detail="O serviço de casas ainda não foi implementado.",
        ) from erro

    return ServicoCasa(supabase)


@router.post("/", response_model=CasaResposta, status_code=201)
def criar_casa(casa: CasaCriar, supabase=Depends(get_supabase)):
    servico = _obter_servico_casa(supabase)
    return servico.criar_casa(casa)


@router.get("/", response_model=list[CasaResposta])
def listar_casas(
    inicio: int = 0,
    limite: int = 100,
    supabase=Depends(get_supabase),
):
    servico = _obter_servico_casa(supabase)
    return servico.listar_casas(inicio, limite)


@router.get("/{id_casa}", response_model=CasaResposta)
def buscar_casa(id_casa: UUID, supabase=Depends(get_supabase)):
    servico = _obter_servico_casa(supabase)
    return servico.buscar_casa(id_casa)


@router.patch("/{id_casa}", response_model=CasaResposta)
def atualizar_casa(
    id_casa: UUID,
    dados: CasaAtualizar,
    supabase=Depends(get_supabase),
):
    servico = _obter_servico_casa(supabase)
    return servico.atualizar_casa(id_casa, dados)


@router.delete("/{id_casa}", response_model=bool)
def excluir_casa(id_casa: UUID, supabase=Depends(get_supabase)):
    servico = _obter_servico_casa(supabase)
    return servico.excluir_casa(id_casa)
