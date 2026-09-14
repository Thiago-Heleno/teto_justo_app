import base64
import binascii
from uuid import UUID

from fastapi import HTTPException

from schemas.casa import CasaAtualizar, CasaCriar


class ServicoCasa:
    def __init__(self, cliente_supabase):
        self.supabase = cliente_supabase

    @staticmethod
    def _foto_para_banco(foto: str) -> str:
        try:
            conteudo = base64.b64decode(foto, validate=True)
        except (binascii.Error, ValueError) as erro:
            raise HTTPException(
                status_code=400,
                detail="A foto deve estar em Base64 válido.",
            ) from erro

        return "\\x" + conteudo.hex()

    @staticmethod
    def _foto_para_resposta(foto: str | None) -> str | None:
        if foto is None:
            return None

        if not isinstance(foto, str) or not foto.startswith("\\x"):
            raise HTTPException(
                status_code=500,
                detail="Formato de foto inválido no banco.",
            )

        try:
            conteudo = bytes.fromhex(foto[2:])
        except ValueError as erro:
            raise HTTPException(
                status_code=500,
                detail="Formato de foto inválido no banco.",
            ) from erro

        return base64.b64encode(conteudo).decode("ascii")

    def _montar_resposta(self, casa: dict) -> dict:
        return {
            "id": casa["id"],
            "nome": casa["nome"],
            "endereco": casa["endereco"],
            "foto": self._foto_para_resposta(casa.get("foto")),
            "fk_usuario_id": casa["fk_usuario_id"],
        }

    def _buscar_casa_bruta(self, id_casa: UUID):
        resposta = (
            self.supabase.table("casa")
            .select("*")
            .eq("id", str(id_casa))
            .execute()
        )

        if not resposta.data:
            raise HTTPException(
                status_code=404,
                detail="Casa não encontrada.",
            )

        return resposta.data[0]

    def criar_casa(self, dados_casa: CasaCriar):
        dados = dados_casa.model_dump(mode="json")

        if dados["foto"] is not None:
            dados["foto"] = self._foto_para_banco(dados["foto"])

        resposta = (
            self.supabase.table("casa")
            .insert(dados)
            .execute()
        )

        if not resposta.data:
            raise HTTPException(
                status_code=500,
                detail="Erro ao criar casa no banco.",
            )

        return self._montar_resposta(resposta.data[0])

    def buscar_casa(self, id_casa: UUID):
        return self._montar_resposta(
            self._buscar_casa_bruta(id_casa)
        )

    def listar_casas(self, inicio: int = 0, limite: int = 100):
        resposta = (
            self.supabase.table("casa")
            .select("*")
            .range(inicio, inicio + limite - 1)
            .execute()
        )

        return [
            self._montar_resposta(casa)
            for casa in resposta.data
        ]

    def atualizar_casa(
        self,
        id_casa: UUID,
        dados_casa: CasaAtualizar,
    ):
        dados = dados_casa.model_dump(
            mode="json",
            exclude_unset=True,
            exclude_none=True,
        )

        if not dados:
            raise HTTPException(
                status_code=400,
                detail="Nenhum dado para atualização.",
            )

        if "foto" in dados:
            dados["foto"] = self._foto_para_banco(dados["foto"])

        resposta = (
            self.supabase.table("casa")
            .update(dados)
            .eq("id", str(id_casa))
            .execute()
        )

        if not resposta.data:
            raise HTTPException(
                status_code=404,
                detail="Casa não encontrada.",
            )

        return self._montar_resposta(resposta.data[0])

    def excluir_casa(self, id_casa: UUID):
        resposta = (
            self.supabase.table("casa")
            .delete()
            .eq("id", str(id_casa))
            .execute()
        )

        if not resposta.data:
            raise HTTPException(
                status_code=404,
                detail="Casa não encontrada.",
            )

        return True
