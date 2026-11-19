"""Integração real de listas de compras e itens com o Supabase de teste."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core.database import get_supabase
from main import app


@pytest.fixture
def cenario_lista(autenticacao_temporaria, criar_autenticacao_temporaria):
    supabase = get_supabase()
    admin = autenticacao_temporaria
    morador = criar_autenticacao_temporaria()
    forasteiro = criar_autenticacao_temporaria()

    with TestClient(app, raise_server_exceptions=False) as cliente:
        criada = cliente.post(
            "/casas/",
            headers=admin["headers"],
            json={
                "nome": f"Casa lista {uuid4().hex}",
                "endereco": "Rua da Lista, 10",
            },
        )
        assert criada.status_code == 201, criada.text
        casa = criada.json()

        supabase.table("pertencer").insert(
            {
                "fk_usuario_id": morador["usuario_id"],
                "fk_casa_id": casa["id"],
                "score": 0,
            }
        ).execute()

        yield (
            cliente,
            casa,
            {
                "administrador": admin,
                "morador": morador,
                "forasteiro": forasteiro,
            },
        )

    supabase.table("lista_compra").delete().eq("fk_casa_id", casa["id"]).execute()
    supabase.table("pertencer").delete().eq("fk_casa_id", casa["id"]).execute()
    supabase.table("casa").delete().eq("id", casa["id"]).execute()


def test_crud_lista_e_itens_no_supabase(cenario_lista):
    cliente, casa, atores = cenario_lista
    admin_headers = atores["administrador"]["headers"]
    morador_headers = atores["morador"]["headers"]
    forasteiro_headers = atores["forasteiro"]["headers"]

    criada = cliente.post(
        "/lista/",
        headers=morador_headers,
        json={"nome": "Mercado da semana", "fk_casa_id": casa["id"]},
    )
    assert criada.status_code == 201, criada.text
    lista = criada.json()
    assert lista["nome"] == "Mercado da semana"
    assert lista["fk_casa_id"] == casa["id"]

    assert cliente.get(f"/lista/casa/{casa['id']}", headers=forasteiro_headers).status_code == 403

    listas = cliente.get(f"/lista/casa/{casa['id']}", headers=morador_headers)
    assert listas.status_code == 200, listas.text
    assert [item["id"] for item in listas.json()] == [lista["id"]]

    renomeada = cliente.patch(
        f"/lista/{lista['id']}",
        headers=morador_headers,
        json={"nome": "Supermercado"},
    )
    assert renomeada.status_code == 200, renomeada.text
    assert renomeada.json()["nome"] == "Supermercado"

    item_a = cliente.post(
        "/lista/itens",
        headers=morador_headers,
        json={"nome": "Café", "quantidade": 2, "fk_lista_id": lista["id"]},
    )
    assert item_a.status_code == 201, item_a.text
    cafe = item_a.json()
    assert cafe["fk_usuario_criador_id"] == atores["morador"]["usuario_id"]
    assert cafe["comprado"] is False

    item_b = cliente.post(
        "/lista/itens",
        headers=admin_headers,
        json={"nome": "Leite", "quantidade": 3, "fk_lista_id": lista["id"]},
    )
    assert item_b.status_code == 201, item_b.text

    itens = cliente.get(f"/lista/{lista['id']}/itens", headers=morador_headers)
    assert itens.status_code == 200, itens.text
    assert [item["nome"] for item in itens.json()] == ["Café", "Leite"]

    editado = cliente.patch(
        f"/lista/itens/{cafe['id']}",
        headers=morador_headers,
        json={"nome": "Café moído", "quantidade": 4},
    )
    assert editado.status_code == 200, editado.text
    assert editado.json()["nome"] == "Café moído"
    assert editado.json()["quantidade"] == 4

    comprado = cliente.post(f"/lista/itens/{cafe['id']}/comprado", headers=admin_headers)
    assert comprado.status_code == 200, comprado.text
    assert comprado.json()["comprado"] is True
    assert comprado.json()["fk_usuario_comprador_id"] == atores["administrador"]["usuario_id"]
    assert comprado.json()["comprado_em"] is not None

    desmarcado = cliente.delete(f"/lista/itens/{cafe['id']}/comprado", headers=morador_headers)
    assert desmarcado.status_code == 200, desmarcado.text
    assert desmarcado.json()["comprado"] is False
    assert desmarcado.json()["fk_usuario_comprador_id"] is None
    assert desmarcado.json()["comprado_em"] is None

    assert (
        cliente.delete(f"/lista/itens/{cafe['id']}", headers=forasteiro_headers).status_code == 403
    )
    assert cliente.delete(f"/lista/itens/{cafe['id']}", headers=morador_headers).status_code == 204

    assert cliente.delete(f"/lista/{lista['id']}", headers=morador_headers).status_code == 403
    assert cliente.delete(f"/lista/{lista['id']}", headers=admin_headers).status_code == 204

    assert cliente.get(f"/lista/{lista['id']}/itens", headers=admin_headers).status_code == 404
