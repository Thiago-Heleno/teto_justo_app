from uuid import UUID

from fastapi import HTTPException, status


class ServicoAutorizacaoCasa:
    TAMANHO_PAGINA = 500
    TAMANHO_LOTE = 100

    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def registros_por_ids(
        self,
        tabela: str,
        campo: str,
        ids: list[str],
        campos: str,
        ordem: tuple[str, ...],
        ativo: bool = False,
    ) -> list[dict]:
        registros = []
        for posicao in range(0, len(ids), self.TAMANHO_LOTE):
            lote = ids[posicao:posicao + self.TAMANHO_LOTE]
            inicio = 0
            while True:
                consulta = self.supabase.table(tabela).select(campos).in_(campo, lote)
                if ativo:
                    consulta = consulta.eq("ativo", True)
                for campo_ordem in ordem:
                    consulta = consulta.order(campo_ordem)
                pagina = (
                    consulta.range(inicio, inicio + self.TAMANHO_PAGINA - 1).execute()
                ).data or []
                registros.extend(pagina)
                if len(pagina) < self.TAMANHO_PAGINA:
                    break
                inicio += self.TAMANHO_PAGINA
        return registros

    def ids_casas_acessiveis(self, id_usuario: UUID | str) -> list[str]:
        ids = set()
        for tabela, campo_filtro, campo_id in (
            ("casa", "fk_usuario_id", "id"),
            ("pertencer", "fk_usuario_id", "fk_casa_id"),
        ):
            inicio = 0
            while True:
                consulta = (
                    self.supabase.table(tabela)
                    .select(campo_id)
                    .eq(campo_filtro, str(id_usuario))
                )
                if tabela == "pertencer":
                    consulta = consulta.eq("ativo", True)
                pagina = (
                    consulta.order(campo_id)
                    .range(inicio, inicio + self.TAMANHO_PAGINA - 1)
                    .execute()
                ).data or []
                ids.update(str(registro[campo_id]) for registro in pagina if registro.get(campo_id))
                if len(pagina) < self.TAMANHO_PAGINA:
                    break
                inicio += self.TAMANHO_PAGINA
        return sorted(ids)

    def garantir_acesso(self, id_casa: UUID | str, id_usuario: UUID | str) -> None:
        casa = (
            self.supabase.table("casa")
            .select("fk_usuario_id")
            .eq("id", str(id_casa))
            .limit(1)
            .execute()
        ).data or []
        if not casa:
            raise HTTPException(status_code=404, detail="Casa não encontrada.")
        if str(casa[0]["fk_usuario_id"]) == str(id_usuario):
            return
        vinculo = (
            self.supabase.table("pertencer")
            .select("fk_usuario_id")
            .eq("fk_casa_id", str(id_casa))
            .eq("fk_usuario_id", str(id_usuario))
            .eq("ativo", True)
            .limit(1)
            .execute()
        ).data or []
        if not vinculo:
            raise HTTPException(status_code=403, detail="Acesso restrito aos moradores da casa.")

    def ids_usuarios_visiveis(self, id_usuario: UUID | str) -> list[str]:
        ids_casas = self.ids_casas_acessiveis(id_usuario)
        ids = {str(id_usuario)}
        for vinculo in self.registros_por_ids(
            "pertencer", "fk_casa_id", ids_casas, "fk_usuario_id",
            ("fk_casa_id", "fk_usuario_id"), ativo=True,
        ):
            ids.add(str(vinculo["fk_usuario_id"]))
        for casa in self.registros_por_ids(
            "casa", "id", ids_casas, "fk_usuario_id", ("id",),
        ):
            if casa.get("fk_usuario_id"):
                ids.add(str(casa["fk_usuario_id"]))
        return sorted(ids)

    def garantir_usuario_visivel(
        self, id_alvo: UUID | str, id_usuario: UUID | str
    ) -> None:
        if str(id_alvo) not in self.ids_usuarios_visiveis(id_usuario):
            raise HTTPException(status_code=403, detail="Acesso restrito aos moradores da casa.")

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
