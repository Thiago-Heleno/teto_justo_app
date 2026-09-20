from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest


@pytest.fixture
def criar_autenticacao_temporaria():
    from core.database import get_supabase

    supabase = get_supabase()
    autenticacoes_criadas = []

    def criar():
        marcador = uuid4().hex
        token = f"teste-autenticacao-{marcador}"
        resposta_usuario = (
            supabase.table("usuario")
            .insert(
                {
                    "nome": "Usuário autenticador de teste",
                    "email": f"teste-autenticacao-{marcador}@example.com",
                    "senha_hash": "nao-utilizada-neste-teste",
                    "usuario_tipo": 0,
                }
            )
            .execute()
        )
        assert resposta_usuario.data, (
            "Não foi possível preparar o usuário autenticador."
        )
        usuario_id = resposta_usuario.data[0]["id"]

        try:
            resposta_sessao = (
                supabase.table("sessao")
                .insert(
                    {
                        "token": token,
                        "expira_em": (
                            datetime.now(timezone.utc) + timedelta(hours=1)
                        ).isoformat(),
                        "fk_usuario_id": usuario_id,
                    }
                )
                .execute()
            )
            assert resposta_sessao.data, (
                "Não foi possível preparar a sessão autenticada."
            )
        except Exception:
            supabase.table("usuario").delete().eq(
                "id", usuario_id
            ).execute()
            raise

        autenticacao = {
            "usuario_id": usuario_id,
            "headers": {"Authorization": f"Bearer {token}"},
        }
        autenticacoes_criadas.append({"token": token, **autenticacao})
        return autenticacao

    yield criar

    for autenticacao in reversed(autenticacoes_criadas):
        try:
            supabase.table("sessao").delete().eq(
                "token", autenticacao["token"]
            ).execute()
        finally:
            supabase.table("pertencer").delete().eq(
                "fk_usuario_id", autenticacao["usuario_id"]
            ).execute()
            supabase.table("atribuida").delete().eq(
                "fk_usuario_id", autenticacao["usuario_id"]
            ).execute()
            supabase.table("usuario").delete().eq(
                "id", autenticacao["usuario_id"]
            ).execute()


@pytest.fixture
def autenticacao_temporaria(criar_autenticacao_temporaria):
    return criar_autenticacao_temporaria()
