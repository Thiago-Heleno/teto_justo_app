from uuid import UUID

from fastapi import HTTPException

from schemas.sessao import SessaoAtualizar, SessaoCriar


class ServicoSessao:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def criar_sessao(self, dados_sessao: SessaoCriar):
        resposta = (
            self.supabase.table("sessao")
            .insert(dados_sessao.model_dump(mode="json"))
            .execute()
        )
        if not resposta.data:
            raise HTTPException(
                status_code=500,
                detail="Erro ao criar sessão no banco.",
            )
        return resposta.data[0]

    def buscar_sessao(self, id_sessao: UUID):
        resposta = (
            self.supabase.table("sessao")
            .select("*")
            .eq("id", str(id_sessao))
            .execute()
        )
        if not resposta.data:
            raise HTTPException(status_code=404, detail="Sessão não encontrada.")
        return resposta.data[0]

    def listar_sessoes(self, inicio: int = 0, limite: int = 100):
        resposta = (
            self.supabase.table("sessao")
            .select("*")
            .range(inicio, inicio + limite - 1)
            .execute()
        )
        return resposta.data

    def atualizar_sessao(self, id_sessao: UUID, dados_sessao: SessaoAtualizar):
        dados = dados_sessao.model_dump(
            mode="json",
            exclude_unset=True,
            exclude_none=True,
        )
        if not dados:
            raise HTTPException(
                status_code=400,
                detail="Nenhum dado para atualização.",
            )

        resposta = (
            self.supabase.table("sessao")
            .update(dados)
            .eq("id", str(id_sessao))
            .execute()
        )
        if not resposta.data:
            raise HTTPException(status_code=404, detail="Sessão não encontrada.")
        return resposta.data[0]

    def excluir_sessao(self, id_sessao: UUID):
        resposta = (
            self.supabase.table("sessao")
            .delete()
            .eq("id", str(id_sessao))
            .execute()
        )
        if not resposta.data:
            raise HTTPException(status_code=404, detail="Sessão não encontrada.")
        return True
