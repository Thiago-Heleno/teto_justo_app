import base64
import binascii
from uuid import UUID

from fastapi import HTTPException
from postgrest.exceptions import APIError

from schemas.casa import CasaAtualizar, CasaCriar
from schemas.pertencer import PertencerCriar
from services.autorizacao import ServicoAutorizacaoCasa
from services.pertencer import ServicoPertencer


class ServicoCasa:
    TAMANHO_PAGINA = 500

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
            "timezone": casa.get("timezone") or "America/Sao_Paulo",
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

    def criar_casa(self, dados_casa: CasaCriar, id_proprietario: UUID):
        dados = dados_casa.model_dump(mode="json")
        dados["fk_usuario_id"] = str(id_proprietario)

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

        casa = resposta.data[0]
        try:
            vinculo = (
                self.supabase.table("pertencer")
                .insert({
                    "fk_usuario_id": str(id_proprietario),
                    "fk_casa_id": casa["id"],
                    "score": 0,
                })
                .execute()
            )
            if not vinculo.data:
                raise RuntimeError("Vínculo do proprietário não foi criado.")
        except Exception as erro:
            self.supabase.table("casa").delete().eq("id", casa["id"]).execute()
            raise HTTPException(
                status_code=500,
                detail="Erro ao vincular o proprietário à casa.",
            ) from erro

        return self._montar_resposta(casa)

    def buscar_casa(self, id_casa: UUID):
        return self._montar_resposta(
            self._buscar_casa_bruta(id_casa)
        )

    def _registros_do_usuario(self, tabela: str, campos: str, filtro: str, id_usuario: UUID):
        inicio = 0
        while True:
            consulta = (
                self.supabase.table(tabela)
                .select(campos)
                .eq(filtro, str(id_usuario))
            )
            if tabela == "pertencer":
                consulta = consulta.eq("ativo", True)
            pagina = (
                consulta.order("id" if tabela == "casa" else "fk_casa_id")
                .range(inicio, inicio + self.TAMANHO_PAGINA - 1)
                .execute()
            ).data or []
            yield from pagina
            if len(pagina) < self.TAMANHO_PAGINA:
                break
            inicio += self.TAMANHO_PAGINA

    def listar_casas(self, id_usuario: UUID, inicio: int = 0, limite: int = 100):
        casas = {
            str(casa["id"]): casa
            for casa in self._registros_do_usuario(
                "casa", "*", "fk_usuario_id", id_usuario
            )
        }
        ids_vinculados = {
            str(vinculo["fk_casa_id"])
            for vinculo in self._registros_do_usuario(
                "pertencer", "fk_casa_id", "fk_usuario_id", id_usuario
            )
        }
        ids_vinculados.difference_update(casas)

        ids_ordenados = sorted(ids_vinculados)
        for posicao in range(0, len(ids_ordenados), self.TAMANHO_PAGINA):
            lote = ids_ordenados[posicao:posicao + self.TAMANHO_PAGINA]
            resposta = (
                self.supabase.table("casa").select("*").in_("id", lote).execute()
            )
            casas.update({str(casa["id"]): casa for casa in resposta.data or []})

        pagina = sorted(casas.values(), key=lambda casa: str(casa["id"]))[
            inicio:inicio + limite
        ]
        return [self._montar_resposta(casa) for casa in pagina]

    def entrar_casa(self, id_casa: UUID, id_emissor: UUID, id_usuario: UUID):
        casa = self._buscar_casa_bruta(id_casa)
        if str(casa["fk_usuario_id"]) != str(id_emissor):
            raise HTTPException(status_code=400, detail="Convite inválido ou expirado.")

        resposta = self._montar_resposta(casa)
        vinculo_ativo = (
            self.supabase.table("pertencer")
            .select("fk_usuario_id")
            .eq("fk_usuario_id", str(id_usuario))
            .eq("fk_casa_id", str(id_casa))
            .eq("ativo", True)
            .execute()
        )
        if vinculo_ativo.data:
            return resposta

        try:
            ServicoPertencer(self.supabase).criar_pertencer(
                PertencerCriar(fk_usuario_id=id_usuario, fk_casa_id=id_casa)
            )
        except HTTPException as erro:
            if (
                erro.status_code == 400
                and erro.detail == "Usuário já pertence a esta casa."
            ) or (
                erro.status_code == 409
                and erro.detail == "O vínculo mudou. Tente novamente."
            ):
                if self._vinculo_ativo(id_casa, id_usuario):
                    return resposta
            raise
        except APIError as erro:
            if erro.code != "23505":
                raise
            if not self._vinculo_ativo(id_casa, id_usuario):
                raise
        return resposta

    def _vinculo_ativo(self, id_casa: UUID, id_usuario: UUID) -> bool:
        return bool((
            self.supabase.table("pertencer")
            .select("fk_usuario_id")
            .eq("fk_usuario_id", str(id_usuario))
            .eq("fk_casa_id", str(id_casa))
            .eq("ativo", True)
            .execute()
        ).data)

    def atualizar_casa(
        self,
        id_casa: UUID,
        dados_casa: CasaAtualizar,
        id_usuario_atual: UUID,
    ):
        ServicoAutorizacaoCasa(
            self.supabase
        ).garantir_administrador_da_casa(
            id_casa,
            id_usuario_atual,
        )
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

    def excluir_casa(self, id_casa: UUID, id_usuario_atual: UUID):
        ServicoAutorizacaoCasa(
            self.supabase
        ).garantir_administrador_da_casa(
            id_casa,
            id_usuario_atual,
        )
        try:
            resposta = (
                self.supabase.table("casa")
                .delete()
                .eq("id", str(id_casa))
                .execute()
            )
        except APIError as erro:
            if erro.code == "23503":
                raise HTTPException(
                    status_code=409,
                    detail="A casa possui dados vinculados e não pode ser excluída.",
                ) from erro
            raise

        if not resposta.data:
            raise HTTPException(
                status_code=404,
                detail="Casa não encontrada.",
            )

        return True

    def listar_moradores(self, id_casa: UUID):
        self._buscar_casa_bruta(id_casa)

        resposta_pertencer = (
            self.supabase.table("pertencer").select("fk_usuario_id, score")
            .eq("fk_casa_id", str(id_casa)).eq("ativo", True).execute()
        )

        if not resposta_pertencer.data:
            return []

        scores_por_usuario = {
            registro["fk_usuario_id"]:registro["score"]
            for registro in resposta_pertencer.data
        }

        resposta_usuarios = (
            self.supabase.table("usuario").select("id, nome, email, telefone, foto")
            .in_("id", list(scores_por_usuario.keys())).execute()
        )

        return [
            {**usuario, "score": scores_por_usuario[usuario["id"]]}
            for usuario in resposta_usuarios.data
        ]



