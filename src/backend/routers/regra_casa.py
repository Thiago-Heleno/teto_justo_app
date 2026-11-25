from uuid import UUID

from fastapi import APIRouter, Depends, status

from core.autenticacao import UsuarioAtual
from core.database import get_supabase
from schemas.regra_casa import (
    MultaCasaCriar,
    MultaCasaResposta,
    RegraCasaAtualizar,
    RegraCasaCriar,
    RegraCasaResposta,
)
from services.regra_casa import ServicoRegraCasa

router = APIRouter(prefix="/regras-casa", tags=["Regras da casa"])


@router.post("/", response_model=RegraCasaResposta, status_code=status.HTTP_201_CREATED)
def criar_regra(dados: RegraCasaCriar, usuario_atual: UsuarioAtual, supabase=Depends(get_supabase)):
    return ServicoRegraCasa(supabase).criar_regra(dados, usuario_atual.id)


@router.get("/casa/{id_casa}", response_model=list[RegraCasaResposta])
def listar_regras(id_casa: UUID, usuario_atual: UsuarioAtual, supabase=Depends(get_supabase)):
    return ServicoRegraCasa(supabase).listar_regras(id_casa, usuario_atual.id)


@router.get("/casa/{id_casa}/multas", response_model=list[MultaCasaResposta])
def listar_multas(id_casa: UUID, usuario_atual: UsuarioAtual, supabase=Depends(get_supabase)):
    return ServicoRegraCasa(supabase).listar_multas(id_casa, usuario_atual.id)


@router.post("/multas", response_model=MultaCasaResposta, status_code=status.HTTP_201_CREATED)
def aplicar_multa(
    dados: MultaCasaCriar, usuario_atual: UsuarioAtual, supabase=Depends(get_supabase)
):
    return ServicoRegraCasa(supabase).aplicar_multa(dados, usuario_atual.id)


@router.post("/multas/{id_multa}/pagar", response_model=MultaCasaResposta)
def pagar_multa(id_multa: UUID, usuario_atual: UsuarioAtual, supabase=Depends(get_supabase)):
    return ServicoRegraCasa(supabase).marcar_paga(id_multa, True, usuario_atual.id)


@router.delete("/multas/{id_multa}/pagar", response_model=MultaCasaResposta)
def desfazer_pagamento(id_multa: UUID, usuario_atual: UsuarioAtual, supabase=Depends(get_supabase)):
    return ServicoRegraCasa(supabase).marcar_paga(id_multa, False, usuario_atual.id)


@router.delete("/multas/{id_multa}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_multa(id_multa: UUID, usuario_atual: UsuarioAtual, supabase=Depends(get_supabase)):
    ServicoRegraCasa(supabase).deletar_multa(id_multa, usuario_atual.id)


@router.patch("/{id_regra}", response_model=RegraCasaResposta)
def atualizar_regra(
    id_regra: UUID,
    dados: RegraCasaAtualizar,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    return ServicoRegraCasa(supabase).atualizar_regra(id_regra, dados, usuario_atual.id)


@router.delete("/{id_regra}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_regra(id_regra: UUID, usuario_atual: UsuarioAtual, supabase=Depends(get_supabase)):
    ServicoRegraCasa(supabase).deletar_regra(id_regra, usuario_atual.id)
