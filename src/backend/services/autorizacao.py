from uuid import UUID

from fastapi import HTTPException, status


class ServicoAutorizacaoCasa:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def garantir_administrador_da_casa(
        self,
        id_casa: UUID | str,
        id_usuario: UUID | str,
    ) -> None:
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
