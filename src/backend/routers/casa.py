from uuid import UUID

from fastapi import APIRouter, Depends

from core.autenticacao import UsuarioAtual
from core.database import get_supabase
from schemas.casa import CasaAtualizar, CasaCriar, CasaResposta, MoradorResposta
from services.casa import ServicoCasa

router = APIRouter(prefix="/casas", tags=["Casas"])


@router.post("/", response_model=CasaResposta, status_code=201)
def criar_casa(
    casa: CasaCriar,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    servico = ServicoCasa(supabase)
    return servico.criar_casa(casa, usuario_atual.id)


@router.get("/", response_model=list[CasaResposta])
def listar_casas(
    usuario_atual: UsuarioAtual,
    inicio: int = 0,
    limite: int = 100,
    supabase=Depends(get_supabase),
):
    servico = ServicoCasa(supabase)
    return servico.listar_casas(inicio, limite)


@router.get("/{id_casa}", response_model=CasaResposta)
def buscar_casa(
    id_casa: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    servico = ServicoCasa(supabase)
    return servico.buscar_casa(id_casa)


@router.patch("/{id_casa}", response_model=CasaResposta)
def atualizar_casa(
    id_casa: UUID,
    dados: CasaAtualizar,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    servico = ServicoCasa(supabase)
    return servico.atualizar_casa(id_casa, dados, usuario_atual.id)


@router.delete("/{id_casa}", response_model=bool)
def excluir_casa(
    id_casa: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    servico = ServicoCasa(supabase)
    return servico.excluir_casa(id_casa, usuario_atual.id)

@router.get("/{id_casa}/moradores", response_model = list[MoradorResposta])
def listar_moradores(id_casa: UUID, usuario_atual: UsuarioAtual, supabase=Depends(get_supabase)):
    return ServicoCasa(supabase).listar_moradores(id_casa)
