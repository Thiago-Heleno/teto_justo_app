from uuid import UUID

from fastapi import HTTPException, status


class ServicoAutorizacaoCasa:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def garantir_administrador_da_casa(
        self,
        id_casa: UUID | str,
        id_usuario: UUID | str,
    ) -> UUID | str:
        resposta = (
            self.supabase.table("casa")
            .select("fk_usuario_id")
            .eq("id", str(id_casa))
            .execute()
        )
        if not resposta.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Casa não encontrada.",
            )

        id_administrador = resposta.data[0].get("fk_usuario_id")
        if str(id_administrador) != str(id_usuario):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão de administrador necessária para esta casa.",
            )
        return id_administrador

    def garantir_responsaveis_da_casa(
        self,
        id_casa: UUID | str,
        ids_usuarios: list[UUID | str],
    ) -> None:
        ids = [str(id_usuario) for id_usuario in ids_usuarios]
        if len(set(ids)) != len(ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Responsáveis duplicados não são permitidos.",
            )

        resposta_casa = (
            self.supabase.table("casa")
            .select("fk_usuario_id")
            .eq("id", str(id_casa))
            .execute()
        )
        if not resposta_casa.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Casa não encontrada.",
            )
        id_administrador = str(resposta_casa.data[0]["fk_usuario_id"])

        resposta_pertencer = (
            self.supabase.table("pertencer")
            .select("fk_usuario_id")
            .eq("fk_casa_id", str(id_casa))
            .eq("ativo", True)
            .execute()
        )
        ids_validos = {
            str(registro["fk_usuario_id"]) for registro in resposta_pertencer.data
        }
        ids_validos.add(id_administrador)

        if any(id_usuario not in ids_validos for id_usuario in ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Um ou mais responsáveis não pertencem a esta casa.",
            )
