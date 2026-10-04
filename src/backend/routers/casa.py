from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from core.autenticacao import UsuarioAtual
from core.database import get_supabase
from schemas.casa import (
    AuditoriaScoreResposta,
    CasaAtualizar,
    CasaConviteResposta,
    CasaCriar,
    CasaPlacarResposta,
    CasaResposta,
    EntrarCasaPedido,
    ErroCasaResposta,
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
from services.convite_casa import ServicoConviteCasa
from services.pertencer import ServicoPertencer
from services.placar import ServicoPlacar

router = APIRouter(
    prefix="/casas",
    tags=["Casas"],
    responses={401: {"model": ErroCasaResposta, "description": "Sessão ausente ou inválida."}},
)

ERRO_400 = {"model": ErroCasaResposta, "description": "Pedido inválido."}
ERRO_403 = {"model": ErroCasaResposta, "description": "Acesso não autorizado para esta casa."}
ERRO_404 = {"model": ErroCasaResposta, "description": "Casa ou vínculo não encontrado."}
ERRO_409 = {"model": ErroCasaResposta, "description": "Operação bloqueada por dados vinculados."}
ERRO_409_ENTRAR = {
    "model": ErroCasaResposta,
    "description": "Vínculo alterado simultaneamente. Tente novamente.",
}
ERRO_503 = {"model": ErroCasaResposta, "description": "Serviço de convites indisponível."}


@router.post("/", response_model=CasaResposta, status_code=201, responses={400: ERRO_400})
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
    inicio: int = Query(0, ge=0),
    limite: int = Query(100, ge=1),
    supabase=Depends(get_supabase),
):
    servico = ServicoCasa(supabase)
    return servico.listar_casas(usuario_atual.id, inicio, limite)


@router.post(
    "/entrar",
    response_model=CasaResposta,
    responses={400: ERRO_400, 404: ERRO_404, 409: ERRO_409_ENTRAR, 503: ERRO_503},
)
def entrar_casa(
    dados: EntrarCasaPedido,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    id_casa, id_emissor = ServicoConviteCasa().verificar(dados.convite)
    return ServicoCasa(supabase).entrar_casa(id_casa, id_emissor, usuario_atual.id)


@router.get("/{id_casa}", response_model=CasaResposta, responses={403: ERRO_403, 404: ERRO_404})
def buscar_casa(
    id_casa: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    ServicoPlacar(supabase).garantir_acesso(id_casa, usuario_atual.id)
    servico = ServicoCasa(supabase)
    return servico.buscar_casa(id_casa)


@router.patch(
    "/{id_casa}",
    response_model=CasaResposta,
    responses={400: ERRO_400, 403: ERRO_403, 404: ERRO_404},
)
def atualizar_casa(
    id_casa: UUID,
    dados: CasaAtualizar,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    servico = ServicoCasa(supabase)
    return servico.atualizar_casa(id_casa, dados, usuario_atual.id)


@router.delete(
    "/{id_casa}",
    response_model=bool,
    responses={403: ERRO_403, 404: ERRO_404, 409: ERRO_409},
)
def excluir_casa(
    id_casa: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    servico = ServicoCasa(supabase)
    return servico.excluir_casa(id_casa, usuario_atual.id)


@router.post(
    "/{id_casa}/convites",
    response_model=CasaConviteResposta,
    responses={403: ERRO_403, 404: ERRO_404, 503: ERRO_503},
)
def criar_convite_casa(
    id_casa: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    ServicoAutorizacaoCasa(supabase).garantir_administrador_da_casa(
        id_casa, usuario_atual.id
    )
    return ServicoConviteCasa().emitir(id_casa, usuario_atual.id)


@router.delete(
    "/{id_casa}/sair",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: ERRO_404, 409: ERRO_409},
)
def sair_casa(
    id_casa: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    ServicoPertencer(supabase).deletar_pertencer(usuario_atual.id, id_casa)


@router.get(
    "/{id_casa}/moradores",
    response_model=list[MoradorResposta],
    responses={403: ERRO_403, 404: ERRO_404},
)
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
