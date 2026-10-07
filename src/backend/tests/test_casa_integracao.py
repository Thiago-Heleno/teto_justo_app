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
@pytest.fixture
def cenario_cargos(autenticacao_temporaria, criar_autenticacao_temporaria):
    """Casa real com um administrador, um morador vinculado e um forasteiro."""
    supabase = get_supabase()
    admin = autenticacao_temporaria
    morador = criar_autenticacao_temporaria()
    forasteiro = criar_autenticacao_temporaria()

    with TestClient(app, raise_server_exceptions=False) as cliente:
        criada = cliente.post(
            "/casas/",
            headers=admin["headers"],
            json={
                "nome": f"Casa cargos {uuid4().hex}",
                "endereco": "Rua dos Cargos, 1",
            },
        )
        assert criada.status_code == 201, criada.text
        casa = criada.json()

        supabase.table("pertencer").insert({
            "fk_usuario_id": morador["usuario_id"],
            "fk_casa_id": casa["id"],
            "score": 0,
        }).execute()

        yield cliente, casa, {
            "administrador": admin["headers"],
            "morador": morador["headers"],
            "forasteiro": forasteiro["headers"],
        }

    supabase.table("pertencer").delete().eq("fk_casa_id", casa["id"]).execute()
    supabase.table("casa").delete().eq("id", casa["id"]).execute()


@pytest.mark.parametrize("cargo,esperado", [
    ("administrador", 200),
    ("morador", 200),
    ("forasteiro", 403),
])
def test_leitura_da_casa_por_cargo_no_supabase(cenario_cargos, cargo, esperado):
    cliente, casa, headers = cenario_cargos

    for rota in (f"/casas/{casa['id']}", f"/casas/{casa['id']}/moradores"):
        resposta = cliente.get(rota, headers=headers[cargo])
        assert resposta.status_code == esperado, resposta.text

    ids = {item["id"] for item in cliente.get("/casas/", headers=headers[cargo]).json()}
    assert (casa["id"] in ids) is (esperado == 200)


@pytest.mark.parametrize("cargo", ["morador", "forasteiro"])
def test_edicao_e_exclusao_negadas_a_quem_nao_e_administrador_no_supabase(
    cenario_cargos, cargo
):
    cliente, casa, headers = cenario_cargos

    edicao = cliente.patch(
        f"/casas/{casa['id']}", headers=headers[cargo], json={"nome": "Invasão"}
    )
    exclusao = cliente.delete(f"/casas/{casa['id']}", headers=headers[cargo])

    assert edicao.status_code == exclusao.status_code == 403
    persistida = (
        get_supabase().table("casa").select("nome").eq("id", casa["id"]).execute()
    ).data
    assert persistida == [{"nome": casa["nome"]}]


def test_administrador_edita_e_exclui_casa_com_morador_no_supabase(cenario_cargos):
    cliente, casa, headers = cenario_cargos
    admin = headers["administrador"]

    edicao = cliente.patch(
        f"/casas/{casa['id']}", headers=admin, json={"nome": "Casa renomeada"}
    )
    assert edicao.status_code == 200, edicao.text
    assert edicao.json()["nome"] == "Casa renomeada"

    exclusao = cliente.delete(f"/casas/{casa['id']}", headers=admin)
    assert exclusao.status_code == 200, exclusao.text
    assert cliente.get(f"/casas/{casa['id']}", headers=admin).status_code == 404
