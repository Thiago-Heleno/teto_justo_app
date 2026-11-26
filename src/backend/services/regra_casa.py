from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException

from schemas.regra_casa import MultaCasaCriar, RegraCasaAtualizar, RegraCasaCriar
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
        multas = (
            self.supabase.table("multa_casa")
            .select("id")
            .eq("fk_regra_id", str(id_regra))
            .limit(1)
            .execute()
        ).data
        if multas:
            raise HTTPException(
                status_code=409, detail="Regra com multas não pode ser excluída. Pause a regra."
            )
        self.supabase.table("regra_casa").delete().eq("id", str(id_regra)).execute()

    def _multa_do_administrador(self, id_multa: UUID, id_usuario: UUID) -> None:
        multa = self.supabase.table("multa_casa").select("*").eq("id", str(id_multa)).execute().data
        if not multa:
            raise HTTPException(status_code=404, detail="Multa não encontrada.")
        self.autorizacao.garantir_administrador_da_casa(multa[0]["fk_casa_id"], id_usuario)

    def listar_multas(self, id_casa: UUID, id_usuario: UUID) -> list[dict]:
        self.autorizacao.garantir_acesso(id_casa, id_usuario)
        return (
            self.supabase.table("multa_casa")
            .select("*")
            .eq("fk_casa_id", str(id_casa))
            .order("criado_em", desc=True)
            .execute()
        ).data

    def aplicar_multa(self, dados: MultaCasaCriar, id_usuario: UUID) -> dict:
        id_administrador = self.autorizacao.garantir_administrador_da_casa(
            dados.fk_casa_id, id_usuario
        )
        regra = self._buscar_regra(dados.fk_regra_id)
        if str(regra["fk_casa_id"]) != str(dados.fk_casa_id):
            raise HTTPException(status_code=422, detail="A regra não pertence a esta casa.")
        if not regra["ativa"]:
            raise HTTPException(status_code=422, detail="A regra está pausada.")
        elegiveis = self.autorizacao.listar_responsaveis_elegiveis(
            dados.fk_casa_id, id_administrador
        )
        if str(dados.fk_usuario_multado_id) not in elegiveis:
            raise HTTPException(status_code=422, detail="O usuário não mora nesta casa.")
        registro = dados.model_dump(mode="json") | {
            "titulo_regra": regra["titulo"],
            "valor_centavos": regra["valor_multa_centavos"],
            "fk_usuario_aplicador_id": str(id_usuario),
        }
        resposta = self.supabase.table("multa_casa").insert(registro).execute()
        if not resposta.data:
            raise HTTPException(status_code=500, detail="Erro ao aplicar multa no banco.")
        return resposta.data[0]

    def marcar_paga(self, id_multa: UUID, paga: bool, id_usuario: UUID) -> dict:
        self._multa_do_administrador(id_multa, id_usuario)
        campos = {
            "paga": paga,
            "pago_em": datetime.now(timezone.utc).isoformat() if paga else None,
        }
        resposta = (
            self.supabase.table("multa_casa").update(campos).eq("id", str(id_multa)).execute()
        )
        if not resposta.data:
            raise HTTPException(status_code=404, detail="Multa não encontrada.")
        return resposta.data[0]

    def deletar_multa(self, id_multa: UUID, id_usuario: UUID) -> None:
        self._multa_do_administrador(id_multa, id_usuario)
        self.supabase.table("multa_casa").delete().eq("id", str(id_multa)).execute()
