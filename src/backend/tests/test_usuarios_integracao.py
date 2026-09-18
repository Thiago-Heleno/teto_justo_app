"""Integração real do CRUD de usuário com o Supabase de teste."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core.database import get_supabase
from main import app


# Payload válido de criação de usuário, com e-mail único por execução para
# evitar colisão com registros de outras rodadas de teste.
@pytest.fixture
def usuario_payload():
    marcador = uuid4().hex
    return {
        "nome": "Usuário teste",
        "email": f"teste-usuario-{marcador}@example.com",
        "telefone": None,
        "senha": "Teste-123!",
        "foto": None,
        "usuario_tipo": 0,
    }


# Acumula os ids de usuários criados durante o teste e os remove do Supabase
# de teste ao final, garantindo que a suíte não deixe dados residuais.
@pytest.fixture
def limpar_usuario():
    ids_criados = []

    yield ids_criados

    supabase = get_supabase()
    for usuario_id in ids_criados:
        supabase.table("usuario").delete().eq("id", usuario_id).execute()


# Percorre o ciclo completo de CRUD via HTTP contra o Supabase real: cria,
# busca, atualiza parcialmente, deleta e confirma que o usuário some depois.
def test_crud_usuario_no_supabase(
    usuario_payload,
    limpar_usuario,
    autenticacao_temporaria,
):
    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente:
        # Cria o usuário e garante que a senha/hash nunca voltam na resposta.
        criado = cliente.post("/usuarios/", json=usuario_payload)
        assert criado.status_code == 201, criado.text
        usuario = criado.json()
        limpar_usuario.append(usuario["id"])
        assert usuario["email"] == usuario_payload["email"]
        assert "senha" not in usuario
        assert "senha_hash" not in usuario

        # Busca o usuário recém-criado por id.
        encontrado = cliente.get(f"/usuarios/{usuario['id']}")
        assert encontrado.status_code == 200, encontrado.text
        assert encontrado.json()["nome"] == usuario_payload["nome"]

        # Atualiza parcialmente apenas o nome.
        atualizado = cliente.patch(
            f"/usuarios/{usuario['id']}",
            json={"nome": "Usuário teste atualizado"},
        )
        assert atualizado.status_code == 200, atualizado.text
        assert atualizado.json()["nome"] == "Usuário teste atualizado"

        # Exclui o usuário e confirma o corpo vazio de um 204.
        excluido = cliente.delete(f"/usuarios/{usuario['id']}")
        assert excluido.status_code == 204, excluido.text
        assert excluido.content == b""

        # Garante que o usuário deixou de existir depois de excluído.
        inexistente = cliente.get(f"/usuarios/{usuario['id']}")
        assert inexistente.status_code == 404


# Garante que a API rejeita a criação de um segundo usuário com o mesmo
# e-mail de um já cadastrado no Supabase real.
def test_email_duplicado_retorna_400(usuario_payload, limpar_usuario):
    with TestClient(app, raise_server_exceptions=False) as cliente:
        primeiro = cliente.post("/usuarios/", json=usuario_payload)
        assert primeiro.status_code == 201, primeiro.text
        limpar_usuario.append(primeiro.json()["id"])

        segundo_payload = dict(usuario_payload, nome="Outro usuário")
        segundo = cliente.post("/usuarios/", json=segundo_payload)
        assert segundo.status_code == 400, segundo.text


# Cobre casos de erro das rotas: payload inválido (422), id malformado (422)
# e operações (GET/PATCH/DELETE) sobre ids inexistentes (404/400).
def test_validacoes_e_erros(usuario_payload, autenticacao_temporaria):
    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente:
        # E-mail em formato inválido.
        assert (
            cliente.post(
                "/usuarios/", json=dict(usuario_payload, email="email-invalido")
            ).status_code
            == 422
        )
        # Payload incompleto, faltando campos obrigatórios.
        assert (
            cliente.post("/usuarios/", json={"nome": "Ana"}).status_code == 422
        )
        # Id que não é um UUID válido.
        assert cliente.get("/usuarios/id-invalido").status_code == 422
        # Busca por um UUID válido, mas inexistente no banco.
        assert cliente.get(f"/usuarios/{uuid4()}").status_code == 404
        # Atualização sem nenhum campo enviado.
        assert (
            cliente.patch(f"/usuarios/{uuid4()}", json={}).status_code == 400
        )
        # Atualização de um usuário inexistente.
        assert (
            cliente.patch(
                f"/usuarios/{uuid4()}", json={"nome": "Alguém"}
            ).status_code
            == 404
        )
        # Exclusão de um usuário inexistente.
        assert cliente.delete(f"/usuarios/{uuid4()}").status_code == 404
