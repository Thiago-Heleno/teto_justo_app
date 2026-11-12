from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException

from schemas.item import ItemCompraAtualizar, ItemCompraCriar
from schemas.lista import ListaCompraAtualizar, ListaCompraCriar
from services.autorizacao import ServicoAutorizacaoCasa


class ServicoLista:
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.autorizacao = ServicoAutorizacaoCasa(supabase_client)

    def _buscar_lista(self, id_lista: UUID) -> dict:
        lista = (
            self.supabase.table("lista_compra").select("*").eq("id", str(id_lista)).execute()
        ).data
        if not lista:
            raise HTTPException(status_code=404, detail="Lista não encontrada.")
        return lista[0]

    def _buscar_item(self, id_item: UUID) -> dict:
        item = self.supabase.table("item_compra").select("*").eq("id", str(id_item)).execute().data
        if not item:
            raise HTTPException(status_code=404, detail="Item não encontrado.")
        return item[0]

    def _lista_com_acesso(self, id_lista: UUID, id_usuario: UUID) -> dict:
        lista = self._buscar_lista(id_lista)
        self.autorizacao.garantir_acesso(lista["fk_casa_id"], id_usuario)
        return lista

    def criar_lista(self, dados: ListaCompraCriar, id_usuario: UUID) -> dict:
        self.autorizacao.garantir_acesso(dados.fk_casa_id, id_usuario)
        resposta = (
            self.supabase.table("lista_compra").insert(dados.model_dump(mode="json")).execute()
        )
        if not resposta.data:
            raise HTTPException(status_code=500, detail="Erro ao criar lista no banco.")
        return resposta.data[0]

    def listar_listas(self, id_casa: UUID, id_usuario: UUID) -> list[dict]:
        self.autorizacao.garantir_acesso(id_casa, id_usuario)
        return (
            self.supabase.table("lista_compra")
            .select("*")
            .eq("fk_casa_id", str(id_casa))
            .order("criado_em")
            .execute()
        ).data

    def atualizar_lista(self, id_lista: UUID, dados: ListaCompraAtualizar, id_usuario: UUID):
        self._lista_com_acesso(id_lista, id_usuario)
        resposta = (
            self.supabase.table("lista_compra")
            .update(dados.model_dump())
            .eq("id", str(id_lista))
            .execute()
        )
        if not resposta.data:
            raise HTTPException(status_code=404, detail="Lista não encontrada.")
        return resposta.data[0]

    def deletar_lista(self, id_lista: UUID, id_usuario: UUID) -> None:
        lista = self._buscar_lista(id_lista)
        self.autorizacao.garantir_administrador_da_casa(lista["fk_casa_id"], id_usuario)
        self.supabase.table("lista_compra").delete().eq("id", str(id_lista)).execute()

    def criar_item(self, dados: ItemCompraCriar, id_usuario: UUID) -> dict:
        self._lista_com_acesso(dados.fk_lista_id, id_usuario)
        registro = dados.model_dump(mode="json") | {"fk_usuario_criador_id": str(id_usuario)}
        resposta = self.supabase.table("item_compra").insert(registro).execute()
        if not resposta.data:
            raise HTTPException(status_code=500, detail="Erro ao criar item no banco.")
        return resposta.data[0]

    def listar_itens(self, id_lista: UUID, id_usuario: UUID) -> list[dict]:
        self._lista_com_acesso(id_lista, id_usuario)
        return (
            self.supabase.table("item_compra")
            .select("*")
            .eq("fk_lista_id", str(id_lista))
            .order("criado_em")
            .execute()
        ).data

    def _item_com_acesso(self, id_item: UUID, id_usuario: UUID) -> dict:
        item = self._buscar_item(id_item)
        self._lista_com_acesso(item["fk_lista_id"], id_usuario)
        return item

    def atualizar_item(self, id_item: UUID, dados: ItemCompraAtualizar, id_usuario: UUID) -> dict:
        self._item_com_acesso(id_item, id_usuario)
        campos = dados.model_dump(exclude_unset=True)
        if not campos:
            raise HTTPException(status_code=422, detail="Nenhum campo para atualizar.")
        return self._atualizar_item_bruto(id_item, campos)

    def marcar_comprado(self, id_item: UUID, comprado: bool, id_usuario: UUID) -> dict:
        self._item_com_acesso(id_item, id_usuario)
        campos = {
            "comprado": comprado,
            "fk_usuario_comprador_id": str(id_usuario) if comprado else None,
            "comprado_em": datetime.now(timezone.utc).isoformat() if comprado else None,
        }
        return self._atualizar_item_bruto(id_item, campos)

    def _atualizar_item_bruto(self, id_item: UUID, campos: dict) -> dict:
        resposta = self.supabase.table("item_compra").update(campos).eq("id", str(id_item)).execute()
        if not resposta.data:
            raise HTTPException(status_code=404, detail="Item não encontrado.")
        return resposta.data[0]

    def deletar_item(self, id_item: UUID, id_usuario: UUID) -> None:
        self._item_com_acesso(id_item, id_usuario)
        self.supabase.table("item_compra").delete().eq("id", str(id_item)).execute()
