"""Integração real do CRUD de casa com o Supabase de teste."""

import base64
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core.database import get_supabase
from main import app

@pytest.fixture
def usuario_temporario(autenticacao_temporaria):
    supabase = get_supabase()
    usuario_id = autenticacao_temporaria["usuario_id"]

    yield usuario_id

    supabase.table("casa").delete().eq(
        "fk_usuario_id", usuario_id
    ).execute()

def test_crud_casa_no_supabase(usuario_temporario, autenticacao_temporaria):
    foto_inicial = base64.b64encode(
        b"fachada inicial"
    ).decode("ascii")

    foto_atualizada = base64.b64encode(
        b"fachada atualizada"
    ).decode("ascii")

    marcador = uuid4().hex

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente:
        criada = cliente.post(
            "/casas/",
            json={
                "nome": f"Casa teste {marcador}",
                "endereco": "Rua de Integração, 100",
                "foto": foto_inicial,
            },
        )

        assert criada.status_code == 201, criada.text

        casa = criada.json()

        assert casa["nome"] == f"Casa teste {marcador}"
        assert casa["endereco"] == "Rua de Integração, 100"
        assert casa["foto"] == foto_inicial
        assert casa["fk_usuario_id"] == usuario_temporario
        assert casa["id"] is not None
        assert casa["timezone"] == "America/Sao_Paulo"

        vinculo_proprietario = (
            get_supabase().table("pertencer")
            .select("score")
            .eq("fk_casa_id", casa["id"])
            .eq("fk_usuario_id", usuario_temporario)
            .execute()
        ).data
        assert vinculo_proprietario == [{"score": 0}]

        remocao_proprietario = cliente.delete(
            f"/pertencer/{usuario_temporario}/{casa['id']}"
        )
        assert remocao_proprietario.status_code == 409, remocao_proprietario.text

        encontrada = cliente.get(
            f"/casas/{casa['id']}"
        )

        assert encontrada.status_code == 200, encontrada.text

        casa_encontrada = encontrada.json()

        assert casa_encontrada["id"] == casa["id"]
        assert casa_encontrada["nome"] == casa["nome"]
        assert casa_encontrada["foto"] == foto_inicial

        listadas = cliente.get("/casas/")

        assert listadas.status_code == 200, listadas.text

        ids = [item["id"] for item in listadas.json()]

        assert casa["id"] in ids

        atualizada = cliente.patch(
            f"/casas/{casa['id']}",
            json={
                "nome": f"Casa atualizada {marcador}",
                "foto": foto_atualizada,
                "timezone": "UTC",
            },
        )

        assert atualizada.status_code == 200, atualizada.text

        casa_atualizada = atualizada.json()

        assert casa_atualizada["nome"] == f"Casa atualizada {marcador}"
        assert casa_atualizada["foto"] == foto_atualizada
        assert casa_atualizada["fk_usuario_id"] == usuario_temporario
        assert casa_atualizada["timezone"] == "UTC"
        excluida = cliente.delete(
            f"/casas/{casa['id']}"
        )

        assert excluida.status_code == 200, excluida.text
        assert excluida.json() is True

        inexistente = cliente.get(
            f"/casas/{casa['id']}"
        )

        assert inexistente.status_code == 404
