from uuid import UUID

from fastapi import APIRouter, Depends, status

from core.autenticacao import UsuarioAtual
from core.database import get_supabase
from schemas.item import ItemCompraAtualizar, ItemCompraCriar, ItemCompraResposta
from schemas.lista import ListaCompraAtualizar, ListaCompraCriar, ListaCompraResposta
from services.lista import ServicoLista

router = APIRouter(prefix="/lista", tags=["Lista"])


@router.post("/", response_model=ListaCompraResposta, status_code=status.HTTP_201_CREATED)
def criar_lista(
    dados: ListaCompraCriar, usuario_atual: UsuarioAtual, supabase=Depends(get_supabase)
):
    return ServicoLista(supabase).criar_lista(dados, usuario_atual.id)


@router.get("/casa/{id_casa}", response_model=list[ListaCompraResposta])
def listar_listas(id_casa: UUID, usuario_atual: UsuarioAtual, supabase=Depends(get_supabase)):
    return ServicoLista(supabase).listar_listas(id_casa, usuario_atual.id)


@router.patch("/{id_lista}", response_model=ListaCompraResposta)
def atualizar_lista(
    id_lista: UUID,
    dados: ListaCompraAtualizar,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    return ServicoLista(supabase).atualizar_lista(id_lista, dados, usuario_atual.id)


@router.delete("/{id_lista}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_lista(id_lista: UUID, usuario_atual: UsuarioAtual, supabase=Depends(get_supabase)):
    ServicoLista(supabase).deletar_lista(id_lista, usuario_atual.id)


@router.get("/{id_lista}/itens", response_model=list[ItemCompraResposta])
def listar_itens(id_lista: UUID, usuario_atual: UsuarioAtual, supabase=Depends(get_supabase)):
    return ServicoLista(supabase).listar_itens(id_lista, usuario_atual.id)


@router.post("/itens", response_model=ItemCompraResposta, status_code=status.HTTP_201_CREATED)
def criar_item(dados: ItemCompraCriar, usuario_atual: UsuarioAtual, supabase=Depends(get_supabase)):
    return ServicoLista(supabase).criar_item(dados, usuario_atual.id)


@router.patch("/itens/{id_item}", response_model=ItemCompraResposta)
def atualizar_item(
    id_item: UUID,
    dados: ItemCompraAtualizar,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    return ServicoLista(supabase).atualizar_item(id_item, dados, usuario_atual.id)


@router.post("/itens/{id_item}/comprado", response_model=ItemCompraResposta)
def marcar_comprado(id_item: UUID, usuario_atual: UsuarioAtual, supabase=Depends(get_supabase)):
    return ServicoLista(supabase).marcar_comprado(id_item, True, usuario_atual.id)


@router.delete("/itens/{id_item}/comprado", response_model=ItemCompraResposta)
def desmarcar_comprado(id_item: UUID, usuario_atual: UsuarioAtual, supabase=Depends(get_supabase)):
    return ServicoLista(supabase).marcar_comprado(id_item, False, usuario_atual.id)


@router.delete("/itens/{id_item}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_item(id_item: UUID, usuario_atual: UsuarioAtual, supabase=Depends(get_supabase)):
    ServicoLista(supabase).deletar_item(id_item, usuario_atual.id)
