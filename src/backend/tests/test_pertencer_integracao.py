"""Integração real dos vínculos de moradores com o Supabase de teste."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core.database import get_supabase
from main import app


# Cria uma casa do usuário autenticado e outro usuário para ser morador.
@pytest.fixture
def dependencias_temporarias(autenticacao_temporaria):
    supabase = get_supabase()
    marcador = uuid4().hex
    proprietario_id = autenticacao_temporaria["usuario_id"]

    # Casa temporária, vinculada ao usuário acima.
    res_casa = (
        supabase.table("casa")
        .insert({
            "nome": f"Casa Teste {marcador}",
            "fk_usuario_id": proprietario_id,
        })
        .execute()
    )
    casa_id = res_casa.data[0]["id"]

    res_morador = (
        supabase.table("usuario")
        .insert({
            "nome": "Morador teste pertencer",
            "email": f"morador-teste-pertencer-{marcador}@example.com",
            "senha_hash": "hash-falso",
            "usuario_tipo": 0,
        })
        .execute()
    )
    usuario_id = res_morador.data[0]["id"]

    yield {"usuario_id": usuario_id, "casa_id": casa_id}

    # Limpeza (teardown): remove o vínculo antes da casa/usuário, pois a FK
    # de fk_usuario_id em pertencer é RESTRICT (não pode sobrar vínculo
    # apontando pra um usuário já excluído).
    supabase.table("pertencer").delete().eq("fk_usuario_id", usuario_id).eq(
        "fk_casa_id", casa_id
    ).execute()
    supabase.table("casa").delete().eq("id", casa_id).execute()
    supabase.table("usuario").delete().eq("id", usuario_id).execute()


# Percorre o ciclo do vínculo via HTTP contra o Supabase real: cria,
# busca, lista, rejeita alteração direta de score, deleta e confirma remoção.
def test_crud_pertencer_no_supabase(
    dependencias_temporarias,
    autenticacao_temporaria,
):
    usuario_id = dependencias_temporarias["usuario_id"]
    casa_id = dependencias_temporarias["casa_id"]

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente:
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

        arbitrario = cliente.post(
            "/pertencer/",
            json={"fk_usuario_id": usuario_id, "fk_casa_id": casa_id, "score": 50},
        )
        assert arbitrario.status_code == 422, arbitrario.text

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

        # O saldo só pode ser alterado por crédito de tarefa.
        atualizado = cliente.patch(
            f"/pertencer/{usuario_id}/{casa_id}", json={"score": 50}
        )
        assert atualizado.status_code == 405, atualizado.text

        # Exclui o vínculo e confirma o corpo vazio de um 204.
        excluido = cliente.delete(f"/pertencer/{usuario_id}/{casa_id}")
        assert excluido.status_code == 204, excluido.text
        assert excluido.content == b""

        # Garante que o vínculo deixou de existir depois de excluído.
        inexistente = cliente.get(f"/pertencer/{usuario_id}/{casa_id}")
        assert inexistente.status_code == 404


# Garante que a API rejeita um segundo vínculo para o mesmo par
# usuário/casa já cadastrado no Supabase real.
def test_pertencer_duplicado_retorna_400(
    dependencias_temporarias,
    autenticacao_temporaria,
):
    usuario_id = dependencias_temporarias["usuario_id"]
    casa_id = dependencias_temporarias["casa_id"]

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente:
        payload = {"fk_usuario_id": usuario_id, "fk_casa_id": casa_id, "score": 0}

        primeiro = cliente.post("/pertencer/", json=payload)
        assert primeiro.status_code == 201, primeiro.text

        segundo = cliente.post("/pertencer/", json=payload)
        assert segundo.status_code == 400, segundo.text


def test_outro_usuario_nao_pode_gerenciar_moradores(
    dependencias_temporarias,
    autenticacao_temporaria,
    criar_autenticacao_temporaria,
):
    usuario_id = dependencias_temporarias["usuario_id"]
    casa_id = dependencias_temporarias["casa_id"]
    outro_usuario = criar_autenticacao_temporaria()

    with TestClient(app, headers=autenticacao_temporaria["headers"]) as dono:
        criado = dono.post(
            "/pertencer/",
            json={"fk_usuario_id": usuario_id, "fk_casa_id": casa_id},
        )
        assert criado.status_code == 201, criado.text

    with TestClient(app, headers=outro_usuario["headers"]) as estranho:
        criado = estranho.post(
            "/pertencer/",
            json={"fk_usuario_id": outro_usuario["usuario_id"], "fk_casa_id": casa_id},
        )
        removido = estranho.delete(f"/pertencer/{usuario_id}/{casa_id}")

    assert criado.status_code == 403
    assert removido.status_code == 403


# Cobre casos de erro das rotas: id malformado (422) e operações
# (GET/PATCH/DELETE) sobre uma chave composta inexistente (404).
def test_validacoes_e_erros(autenticacao_temporaria):
    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente:
        # Um dos ids da chave composta não é um UUID válido.
        assert cliente.get(f"/pertencer/id-invalido/{uuid4()}").status_code == 422
        # Busca por uma chave (usuário, casa) válida, mas inexistente.
        assert cliente.get(f"/pertencer/{uuid4()}/{uuid4()}").status_code == 404
        # Atualização de um vínculo inexistente.
        assert (
            cliente.patch(
                f"/pertencer/{uuid4()}/{uuid4()}", json={"score": 10}
            ).status_code
            == 405
        )
        # Exclusão de um vínculo inexistente.
        assert cliente.delete(f"/pertencer/{uuid4()}/{uuid4()}").status_code == 404
