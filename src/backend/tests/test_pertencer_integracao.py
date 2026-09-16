"""Integração real do CRUD de pertencer com o Supabase de teste."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core.database import get_supabase
from main import app


# Cria um usuário e uma casa temporários no Supabase de teste — dependências
# de FK exigidas por um vínculo de pertencer — e os remove ao final do teste.
@pytest.fixture
def dependencias_temporarias():
    supabase = get_supabase()
    marcador = uuid4().hex

    # Usuário temporário, que também será o dono da casa criada a seguir.
    res_usuario = (
        supabase.table("usuario")
        .insert({
            "nome": "Usuário Teste Pertencer",
            "email": f"teste-pertencer-{marcador}@example.com",
            "senha_hash": "hash-falso",
            "usuario_tipo": 0,
        })
        .execute()
    )
    usuario_id = res_usuario.data[0]["id"]

    # Casa temporária, vinculada ao usuário acima.
    res_casa = (
        supabase.table("casa")
        .insert({
            "nome": f"Casa Teste {marcador}",
            "fk_usuario_id": usuario_id,
        })
        .execute()
    )
    casa_id = res_casa.data[0]["id"]

    yield {"usuario_id": usuario_id, "casa_id": casa_id}

    # Limpeza (teardown): remove o vínculo antes da casa/usuário, pois a FK
    # de fk_usuario_id em pertencer é RESTRICT (não pode sobrar vínculo
    # apontando pra um usuário já excluído).
    supabase.table("pertencer").delete().eq("fk_usuario_id", usuario_id).eq(
        "fk_casa_id", casa_id
    ).execute()
    supabase.table("casa").delete().eq("id", casa_id).execute()
    supabase.table("usuario").delete().eq("id", usuario_id).execute()


# Percorre o ciclo completo de CRUD via HTTP contra o Supabase real: cria,
# busca, lista, atualiza o score, deleta e confirma que o vínculo some depois.
def test_crud_pertencer_no_supabase(dependencias_temporarias):
    usuario_id = dependencias_temporarias["usuario_id"]
    casa_id = dependencias_temporarias["casa_id"]

    with TestClient(app, raise_server_exceptions=False) as cliente:
        # Cria o vínculo entre o usuário e a casa com o score padrão.
        criado = cliente.post(
            "/pertencer/",
            json={"fk_usuario_id": usuario_id, "fk_casa_id": casa_id, "score": 0},
        )
        assert criado.status_code == 201, criado.text
        vinculo = criado.json()
        assert vinculo["fk_usuario_id"] == usuario_id
        assert vinculo["fk_casa_id"] == casa_id
        assert vinculo["score"] == 0

        # Busca o vínculo recém-criado pela chave composta (usuário, casa).
        encontrado = cliente.get(f"/pertencer/{usuario_id}/{casa_id}")
        assert encontrado.status_code == 200, encontrado.text
        assert encontrado.json()["score"] == 0

        # Lista os vínculos e confirma que o criado está entre eles.
        listados = cliente.get("/pertencer/")
        assert listados.status_code == 200, listados.text
        assert any(
            v["fk_usuario_id"] == usuario_id and v["fk_casa_id"] == casa_id
            for v in listados.json()
        )

        # Atualiza o score do vínculo.
        atualizado = cliente.patch(
            f"/pertencer/{usuario_id}/{casa_id}", json={"score": 50}
        )
        assert atualizado.status_code == 200, atualizado.text
        assert atualizado.json()["score"] == 50

        # Exclui o vínculo e confirma o corpo vazio de um 204.
        excluido = cliente.delete(f"/pertencer/{usuario_id}/{casa_id}")
        assert excluido.status_code == 204, excluido.text
        assert excluido.content == b""

        # Garante que o vínculo deixou de existir depois de excluído.
        inexistente = cliente.get(f"/pertencer/{usuario_id}/{casa_id}")
        assert inexistente.status_code == 404


# Garante que a API rejeita um segundo vínculo para o mesmo par
# usuário/casa já cadastrado no Supabase real.
def test_pertencer_duplicado_retorna_400(dependencias_temporarias):
    usuario_id = dependencias_temporarias["usuario_id"]
    casa_id = dependencias_temporarias["casa_id"]

    with TestClient(app, raise_server_exceptions=False) as cliente:
        payload = {"fk_usuario_id": usuario_id, "fk_casa_id": casa_id, "score": 0}

        primeiro = cliente.post("/pertencer/", json=payload)
        assert primeiro.status_code == 201, primeiro.text

        segundo = cliente.post("/pertencer/", json=payload)
        assert segundo.status_code == 400, segundo.text


# Cobre casos de erro das rotas: id malformado (422) e operações
# (GET/PATCH/DELETE) sobre uma chave composta inexistente (404).
def test_validacoes_e_erros():
    with TestClient(app, raise_server_exceptions=False) as cliente:
        # Um dos ids da chave composta não é um UUID válido.
        assert cliente.get(f"/pertencer/id-invalido/{uuid4()}").status_code == 422
        # Busca por uma chave (usuário, casa) válida, mas inexistente.
        assert cliente.get(f"/pertencer/{uuid4()}/{uuid4()}").status_code == 404
        # Atualização de um vínculo inexistente.
        assert (
            cliente.patch(
                f"/pertencer/{uuid4()}/{uuid4()}", json={"score": 10}
            ).status_code
            == 404
        )
        # Exclusão de um vínculo inexistente.
        assert cliente.delete(f"/pertencer/{uuid4()}/{uuid4()}").status_code == 404
