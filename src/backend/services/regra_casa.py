from uuid import UUID

from fastapi import HTTPException

from schemas.regra_casa import RegraCasaAtualizar, RegraCasaCriar
from services.autorizacao import ServicoAutorizacaoCasa


class ServicoRegraCasa:
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.autorizacao = ServicoAutorizacaoCasa(supabase_client)

    def _buscar_regra(self, id_regra: UUID) -> dict:
        regra = self.supabase.table("regra_casa").select("*").eq("id", str(id_regra)).execute().data
        if not regra:
            raise HTTPException(status_code=404, detail="Regra não encontrada.")
        return regra[0]

    def _regra_do_administrador(self, id_regra: UUID, id_usuario: UUID) -> dict:
        regra = self._buscar_regra(id_regra)
        self.autorizacao.garantir_administrador_da_casa(regra["fk_casa_id"], id_usuario)
        return regra

    def listar_regras(self, id_casa: UUID, id_usuario: UUID) -> list[dict]:
        self.autorizacao.garantir_acesso(id_casa, id_usuario)
        return (
            self.supabase.table("regra_casa")
            .select("*")
            .eq("fk_casa_id", str(id_casa))
            .order("criado_em")
            .execute()
        ).data

    def criar_regra(self, dados: RegraCasaCriar, id_usuario: UUID) -> dict:
        self.autorizacao.garantir_administrador_da_casa(dados.fk_casa_id, id_usuario)
        resposta = self.supabase.table("regra_casa").insert(dados.model_dump(mode="json")).execute()
        if not resposta.data:
            raise HTTPException(status_code=500, detail="Erro ao criar regra no banco.")
        return resposta.data[0]

    def atualizar_regra(self, id_regra: UUID, dados: RegraCasaAtualizar, id_usuario: UUID) -> dict:
        self._regra_do_administrador(id_regra, id_usuario)
        campos = dados.model_dump(exclude_unset=True)
        if not campos:
            raise HTTPException(status_code=422, detail="Nenhum campo para atualizar.")
        resposta = (
            self.supabase.table("regra_casa").update(campos).eq("id", str(id_regra)).execute()
        )
        if not resposta.data:
            raise HTTPException(status_code=404, detail="Regra não encontrada.")
        return resposta.data[0]

    def deletar_regra(self, id_regra: UUID, id_usuario: UUID) -> None:
        self._regra_do_administrador(id_regra, id_usuario)
        self.supabase.table("regra_casa").delete().eq("id", str(id_regra)).execute()
