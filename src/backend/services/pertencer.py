from uuid import UUID
from fastapi import HTTPException
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
            if existente.data[0]["ativo"]:
                raise HTTPException(
                    status_code=400,
                    detail="Usuário já pertence a esta casa.",
                )
            resposta = (
                self.supabase.table("pertencer")
                .update({"ativo": True})
                .eq("fk_usuario_id", str(dados.fk_usuario_id))
                .eq("fk_casa_id", str(dados.fk_casa_id))
                .eq("ativo", False)
                .execute()
            )
            if not resposta.data:
                raise HTTPException(
                    status_code=409, detail="O vínculo mudou. Tente novamente."
                )
            return resposta.data[0]

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
            .eq("ativo", True)
            .execute()
        )

        if not resposta.data:
            raise HTTPException(status_code=404, detail="Vínculo não encontrado.")

        return resposta.data[0]

    def listar_pertencer(self, inicio: int = 0, limite: int = 100):
        resposta = (
            self.supabase.table("pertencer")
            .select("*")
            .eq("ativo", True)
            .range(inicio, inicio + limite - 1)
            .execute()
        )
        return resposta.data

    def deletar_pertencer(self, fk_usuario_id: UUID, fk_casa_id: UUID):

        casa = (
            self.supabase.table("casa")
            .select("fk_usuario_id, rotacao_versao")
            .eq("id", str(fk_casa_id))
            .execute()
        ).data
        if not casa:
            raise HTTPException(
                status_code=404,
                detail="Vínculo não encontrado ou já deletado.",
            )
        if str(casa[0]["fk_usuario_id"]) == str(fk_usuario_id):
            raise HTTPException(
                status_code=409,
                detail="O proprietário não pode sair da própria casa.",
            )
        vinculo = (
            self.supabase.table("pertencer")
            .select("fk_usuario_id")
            .eq("fk_usuario_id", str(fk_usuario_id))
            .eq("fk_casa_id", str(fk_casa_id))
            .eq("ativo", True)
            .execute()
        )
        if not vinculo.data:
            raise HTTPException(
                status_code=404,
                detail="Vínculo não encontrado ou já deletado.",
            )
        ids_tarefas = [
            registro["fk_tarefa_id"]
            for registro in (
                self.supabase.table("atribuida")
                .select("fk_tarefa_id")
                .eq("fk_usuario_id", str(fk_usuario_id))
                .execute()
            ).data
        ]
        if ids_tarefas:
            tarefas_abertas = (
                self.supabase.table("tarefa")
                .select("id")
                .in_("id", ids_tarefas)
                .eq("fk_casa_id", str(fk_casa_id))
                .in_("estado_atual", ["pendente", "atrasada"])
                .execute()
            )
            if tarefas_abertas.data:
                raise HTTPException(
                    status_code=409,
                    detail="O morador possui tarefas abertas nesta casa.",
                )
        resposta = (
            self.supabase.table("pertencer")
            .update({"ativo": False})
            .eq("fk_usuario_id", str(fk_usuario_id))
            .eq("fk_casa_id", str(fk_casa_id))
            .eq("ativo", True)
            .execute()
        )
        if not resposta.data:
            raise HTTPException(
                status_code=404, detail="Vínculo não encontrado ou já deletado."
            )
        self.supabase.table("casa").update(
            {"rotacao_versao": casa[0]["rotacao_versao"] + 1}
        ).eq("id", str(fk_casa_id)).execute()

        return True
