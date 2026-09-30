from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from core.autenticacao import UsuarioAtual
from core.database import get_supabase
from schemas.casa import (
    AuditoriaScoreResposta,
    CasaAtualizar,
    CasaCriar,
    CasaPlacarResposta,
    CasaResposta,
    MoradorResposta,
)
from schemas.score import (
    ExtratoScoreResposta,
    FiltroExtratoScore,
    FiltroPeriodoScore,
    RankingScoreResposta,
    SaldoScoreResposta,
)
from services.autorizacao import ServicoAutorizacaoCasa
from services.casa import ServicoCasa
from services.placar import ServicoPlacar

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

@router.get("/{id_casa}/moradores", response_model=list[MoradorResposta])
def listar_moradores(
    id_casa: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    ServicoPlacar(supabase).garantir_acesso(id_casa, usuario_atual.id)
    return ServicoCasa(supabase).listar_moradores(id_casa)


@router.get("/{id_casa}/placar", response_model=CasaPlacarResposta)
def obter_placar(
    id_casa: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    servico = ServicoPlacar(supabase)
    servico.garantir_acesso(id_casa, usuario_atual.id)
    return servico.obter_placar(id_casa)


@router.get("/{id_casa}/saldo", response_model=SaldoScoreResposta)
def obter_saldo(
    id_casa: UUID,
    fk_usuario_id: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    servico = ServicoPlacar(supabase)
    servico.garantir_acesso(id_casa, usuario_atual.id)
    return servico.obter_saldo(id_casa, fk_usuario_id)


@router.get("/{id_casa}/extrato", response_model=ExtratoScoreResposta)
def obter_extrato(
    id_casa: UUID,
    filtros: Annotated[FiltroExtratoScore, Query()],
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    servico = ServicoPlacar(supabase)
    servico.garantir_acesso(id_casa, usuario_atual.id)
    return servico.obter_extrato(id_casa, filtros)


@router.get("/{id_casa}/ranking", response_model=RankingScoreResposta)
def obter_ranking(
    id_casa: UUID,
    filtros: Annotated[FiltroPeriodoScore, Query()],
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    servico = ServicoPlacar(supabase)
    servico.garantir_acesso(id_casa, usuario_atual.id)
    return servico.obter_ranking(id_casa, filtros)


@router.get("/{id_casa}/auditoria-score", response_model=AuditoriaScoreResposta)
def auditar_score(
    id_casa: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    ServicoAutorizacaoCasa(supabase).garantir_administrador_da_casa(
        id_casa, usuario_atual.id
    )
    return {
        "casa_id": str(id_casa),
        "divergencias": ServicoPlacar(supabase).auditar_saldos(id_casa),
    }
