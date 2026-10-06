"""Integração real do login/logout com o Supabase de teste."""

import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from core.database import get_supabase
from main import app
from services.sessao import hash_token_sessao


@pytest.fixture
def usuario_temporario():
    supabase = get_supabase()
    senha = secrets.token_urlsafe(24)
    email = f"teste-sessao-{uuid4().hex}@example.com"
    with TestClient(app) as cliente:
        resposta = cliente.post("/usuarios/", json={
            "nome": "Usuário teste de sessão", "email": email, "senha": senha,
        })
    assert resposta.status_code == 201
    usuario_id = resposta.json()["id"]
    try:
        yield {"id": usuario_id, "email": email, "senha": senha}
    finally:
        supabase.table("sessao").delete().eq("fk_usuario_id", usuario_id).execute()
        supabase.table("usuario").delete().eq("id", usuario_id).execute()


def test_login_logout_no_supabase(usuario_temporario):
    with TestClient(app, raise_server_exceptions=False) as cliente:
        login = cliente.post("/sessoes/login", json={
            "email": usuario_temporario["email"], "senha": usuario_temporario["senha"],
        })
        assert login.status_code == 200
        token = login.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        persistida = (
            get_supabase().table("sessao")
            .select("token")
            .eq("fk_usuario_id", usuario_temporario["id"])
            .execute()
        )
        assert len(persistida.data) == 1
        assert persistida.data[0]["token"] == hash_token_sessao(token)
        eu = cliente.get("/usuarios/eu", headers=headers)
        assert eu.status_code == 200
        assert eu.json()["id"] == usuario_temporario["id"]
        assert "senha_hash" not in eu.json()
        assert cliente.get("/sessoes/", headers=headers).status_code == 404
        logout = cliente.post("/sessoes/logout", headers=headers)
        assert logout.status_code == 204
        assert not logout.content
        assert cliente.get("/usuarios/eu", headers=headers).status_code == 401


def test_hash_de_token_unico_no_supabase(usuario_temporario):
    supabase = get_supabase()
    hash_token = hash_token_sessao(secrets.token_urlsafe(32))
    dados = {
        "token": hash_token,
        "fk_usuario_id": usuario_temporario["id"],
        "expira_em": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }
    try:
        assert supabase.table("sessao").insert(dados).execute().data
        with pytest.raises(APIError) as erro:
            supabase.table("sessao").insert(dados).execute()
        assert erro.value.code == "23505"
    finally:
        supabase.table("sessao").delete().eq("token", hash_token).execute()
