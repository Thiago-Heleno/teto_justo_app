from uuid import UUID

from fastapi import HTTPException
from postgrest.exceptions import APIError

from schemas.pertencer import PertencerCriar


class ServicoPertencer:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def criar_pertencer(self, dados: PertencerCriar):
        existente = (
            self.supabase.table("pertencer")
            .select("*")
            .eq("fk_usuario_id", str(dados.fk_usuario_id))
            .eq("fk_casa_id", str(dados.fk_casa_id))
            .execute()
        )

        if existente.data:
            raise HTTPException(
                status_code=400,
                detail="Usuário já pertence a esta casa.",
            )

        resposta = (
            self.supabase.table("pertencer")
            .insert(dados.model_dump(mode="json"))
            .execute()
        )

        if not resposta.data:
            raise HTTPException(
                status_code=500,
                detail="Erro ao criar vínculo no banco.",
            )

        return resposta.data[0]

    def buscar_pertencer(self, fk_usuario_id: UUID, fk_casa_id: UUID):
        resposta = (
            self.supabase.table("pertencer")
            .select("*")
            .eq("fk_usuario_id", str(fk_usuario_id))
            .eq("fk_casa_id", str(fk_casa_id))
            .execute()
        )

        if not resposta.data:
            raise HTTPException(status_code=404, detail="Vínculo não encontrado.")

        return resposta.data[0]

    def listar_pertencer(self, inicio: int = 0, limite: int = 100):
        resposta = (
            self.supabase.table("pertencer")
            .select("*")
            .range(inicio, inicio + limite - 1)
            .execute()
        )
        return resposta.data

    def deletar_pertencer(self, fk_usuario_id: UUID, fk_casa_id: UUID):
        casa = (
            self.supabase.table("casa")
            .select("fk_usuario_id")
            .eq("id", str(fk_casa_id))
            .execute()
        ).data
        if casa and str(casa[0]["fk_usuario_id"]) == str(fk_usuario_id):
            raise HTTPException(
                status_code=409,
                detail="O proprietário não pode sair da própria casa.",
            )
        try:
            resposta = self.supabase.rpc(
                "excluir_vinculo_sem_credito",
                {
                    "p_id_usuario": str(fk_usuario_id),
                    "p_id_casa": str(fk_casa_id),
                },
            ).execute()
        except APIError as erro:
            if erro.code == "PT409":
                raise HTTPException(status_code=409, detail=erro.message) from erro
            raise
        if resposta.data is not True:
            raise HTTPException(
                status_code=404,
                detail="Vínculo não encontrado ou já deletado.",
            )

        return True
