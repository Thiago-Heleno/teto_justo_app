"""Integração real do CRUD de sessão com o Supabase de teste."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core.database import get_supabase
from main import app


@pytest.fixture
def usuario_temporario():
    supabase = get_supabase()
    marcador = uuid4().hex
    resposta = (
        supabase.table("usuario")
        .insert(
            {
                "nome": "Usuário teste de sessão",
                "email": f"teste-sessao-{marcador}@example.com",
                "senha_hash": "nao-utilizada-neste-teste",
                "usuario_tipo": 0,
            }
        )
        .execute()
    )
    assert resposta.data, "Não foi possível preparar o usuário de teste."
    usuario_id = resposta.data[0]["id"]

    yield usuario_id

    supabase.table("sessao").delete().eq("fk_usuario_id", usuario_id).execute()
    supabase.table("usuario").delete().eq("id", usuario_id).execute()


def test_crud_sessao_no_supabase(usuario_temporario):
    token_inicial = f"teste-{uuid4().hex}"
    token_atualizado = f"teste-{uuid4().hex}"
    expira_em = datetime.now(timezone.utc) + timedelta(days=1)

    with TestClient(app, raise_server_exceptions=False) as cliente:
        criada = cliente.post(
            "/sessoes/",
            json={
                "token": token_inicial,
                "expira_em": expira_em.isoformat(),
                "fk_usuario_id": usuario_temporario,
            },
        )
        assert criada.status_code == 201, criada.text
        sessao = criada.json()
        assert sessao["token"] == token_inicial
        assert sessao["fk_usuario_id"] == usuario_temporario
        assert sessao["criado_em"] is not None

        encontrada = cliente.get(f"/sessoes/{sessao['id']}")
        assert encontrada.status_code == 200, encontrada.text
        assert encontrada.json()["id"] == sessao["id"]

        atualizada = cliente.patch(
            f"/sessoes/{sessao['id']}",
            json={"token": token_atualizado},
        )
        assert atualizada.status_code == 200, atualizada.text
        assert atualizada.json()["token"] == token_atualizado

        excluida = cliente.delete(f"/sessoes/{sessao['id']}")
        assert excluida.status_code == 200, excluida.text
        assert excluida.json() is True

        inexistente = cliente.get(f"/sessoes/{sessao['id']}")
        assert inexistente.status_code == 404
