from uuid import UUID

from fastapi import APIRouter, Depends, status

from core.database import get_supabase
from schemas.pertencer import (
    PertencerAtualizar,
    PertencerCriar,
    PertencerResposta,
)
from services.pertencer import ServicoPertencer


router = APIRouter(prefix="/pertencer", tags=["Pertencer"])


@router.post("/", response_model=PertencerResposta, status_code=status.HTTP_201_CREATED)
def registrar_pertencer(
    pertencer: PertencerCriar,
    supabase=Depends(get_supabase),
):
    return ServicoPertencer(supabase).criar_pertencer(pertencer)


@router.get("/", response_model=list[PertencerResposta])
def listar_pertencer(
    inicio: int = 0,
    limite: int = 100,
    supabase=Depends(get_supabase),
):
    return ServicoPertencer(supabase).listar_pertencer(inicio, limite)


@router.get(
    "/{fk_usuario_id}/{fk_casa_id}",
    response_model=PertencerResposta,
)
def buscar_pertencer(
    fk_usuario_id: UUID,
    fk_casa_id: UUID,
    supabase=Depends(get_supabase),
):
    return ServicoPertencer(supabase).buscar_pertencer(fk_usuario_id, fk_casa_id)


@router.patch(
    "/{fk_usuario_id}/{fk_casa_id}",
    response_model=PertencerResposta,
)
def atualizar_score(
    fk_usuario_id: UUID,
    fk_casa_id: UUID,
    dados: PertencerAtualizar,
    supabase=Depends(get_supabase),
):
    return ServicoPertencer(supabase).atualizar_pertencer(
        fk_usuario_id,
        fk_casa_id,
        dados,
    )


@router.delete(
    "/{fk_usuario_id}/{fk_casa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def deletar_pertencer(
    fk_usuario_id: UUID,
    fk_casa_id: UUID,
    supabase=Depends(get_supabase),
):
    ServicoPertencer(supabase).deletar_pertencer(fk_usuario_id, fk_casa_id)
    return None
