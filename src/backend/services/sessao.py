import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
from fastapi import HTTPException

from schemas.sessao import LoginEntrada, LoginResposta
from schemas.usuario import UsuarioResposta


# Mantém a verificação de bcrypt também quando o e-mail não existe.
_HASH_SENHA_AUSENTE = bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt(rounds=12))


def hash_token_sessao(token: str) -> str:
    return "sha256:" + hashlib.sha256(token.encode("utf-8")).hexdigest()


class ServicoSessao:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def login(self, dados: LoginEntrada) -> LoginResposta:
        resposta = (
            self.supabase.table("usuario")
            .select("id,senha_hash")
            .eq("email", str(dados.email))
            .limit(2)
            .execute()
        )
        usuarios = resposta.data or []
        usuario = usuarios[0] if len(usuarios) == 1 else None
        senha = dados.senha.get_secret_value().encode("utf-8")
        senha_hash = usuario.get("senha_hash") if usuario else None
        try:
            confere = bcrypt.checkpw(
                senha,
                senha_hash.encode("utf-8") if isinstance(senha_hash, str) else _HASH_SENHA_AUSENTE,
            )
        except ValueError:
            confere = False

        if not usuario or not senha_hash or not confere:
            raise HTTPException(
                status_code=401,
                detail="E-mail ou senha inválidos.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = secrets.token_urlsafe(32)
        expira_em = datetime.now(timezone.utc) + timedelta(hours=24)
        criada = (
            self.supabase.table("sessao")
            .insert({
                "token": hash_token_sessao(token),
                "expira_em": expira_em.isoformat(),
                "fk_usuario_id": str(usuario["id"]),
            })
            .execute()
        )
        if not criada.data:
            raise HTTPException(status_code=500, detail="Não foi possível iniciar a sessão.")
        return LoginResposta(token=token, expira_em=expira_em)

    def logout(self, token: str, id_usuario: UUID) -> None:
        (
            self.supabase.table("sessao")
            .delete()
            .eq("token", hash_token_sessao(token))
            .eq("fk_usuario_id", str(id_usuario))
            .execute()
        )

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
            .eq("token", hash_token_sessao(token))
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
