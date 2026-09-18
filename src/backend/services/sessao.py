from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException

from schemas.sessao import SessaoAtualizar, SessaoCriar
from schemas.usuario import UsuarioResposta


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

    @staticmethod
    def _expiracao_em_utc(valor) -> datetime | None:
        if isinstance(valor, datetime):
            expiracao = valor
        elif isinstance(valor, str):
            try:
                expiracao = datetime.fromisoformat(valor.replace("Z", "+00:00"))
            except ValueError:
                return None
        else:
            return None

        # A coluna atual usa TIMESTAMP sem fuso; valores legados são tratados como UTC.
        if expiracao.tzinfo is None:
            expiracao = expiracao.replace(tzinfo=timezone.utc)
        return expiracao.astimezone(timezone.utc)

    def obter_usuario_por_token(self, token: str) -> UsuarioResposta | None:
        resposta_sessao = (
            self.supabase.table("sessao")
            .select("fk_usuario_id,expira_em")
            .eq("token", token)
            .limit(2)
            .execute()
        )
        sessoes = resposta_sessao.data or []
        if len(sessoes) != 1:
            return None

        sessao = sessoes[0]
        expiracao = self._expiracao_em_utc(sessao.get("expira_em"))
        if expiracao is None or expiracao <= datetime.now(timezone.utc):
            return None

        id_usuario = sessao.get("fk_usuario_id")
        if not id_usuario:
            return None

        resposta_usuario = (
            self.supabase.table("usuario")
            .select("id,nome,email,telefone,foto,usuario_tipo,data_criacao")
            .eq("id", str(id_usuario))
            .limit(2)
            .execute()
        )
        usuarios = resposta_usuario.data or []
        if len(usuarios) != 1:
            return None

        return UsuarioResposta.model_validate(usuarios[0])

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
