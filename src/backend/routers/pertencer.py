from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from core.autenticacao import UsuarioAtual
from core.database import get_supabase
from schemas.pertencer import (
    PertencerCriar,
    PertencerResposta,
)
from services.autorizacao import ServicoAutorizacaoCasa
from services.pertencer import ServicoPertencer


router = APIRouter(prefix="/pertencer", tags=["Pertencer"])


@router.post("/", response_model=PertencerResposta, status_code=status.HTTP_201_CREATED)
def registrar_pertencer(
    pertencer: PertencerCriar,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    ServicoAutorizacaoCasa(supabase).garantir_administrador_da_casa(
        pertencer.fk_casa_id, usuario_atual.id
    )
    return ServicoPertencer(supabase).criar_pertencer(pertencer)


@router.get("/", response_model=list[PertencerResposta])
def listar_pertencer(
    usuario_atual: UsuarioAtual,
    inicio: int = Query(0, ge=0),
    limite: int = Query(100, ge=1),
    supabase=Depends(get_supabase),
):
    return ServicoPertencer(supabase).listar_pertencer_acessiveis(
        usuario_atual.id, inicio, limite
    )


@router.get(
    "/{fk_usuario_id}/{fk_casa_id}",
    response_model=PertencerResposta,
)
def buscar_pertencer(
    fk_usuario_id: UUID,
    fk_casa_id: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    ServicoAutorizacaoCasa(supabase).garantir_acesso(fk_casa_id, usuario_atual.id)
    return ServicoPertencer(supabase).buscar_pertencer(fk_usuario_id, fk_casa_id)


@router.delete(
    "/{fk_usuario_id}/{fk_casa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def deletar_pertencer(
    fk_usuario_id: UUID,
    fk_casa_id: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    ServicoAutorizacaoCasa(supabase).garantir_administrador_da_casa(
        fk_casa_id, usuario_atual.id
    )
    ServicoPertencer(supabase).deletar_pertencer(fk_usuario_id, fk_casa_id)
    return None
