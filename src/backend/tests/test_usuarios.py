import random
from fastapi.testclient import TestClient
from main import app  # Verifique se o import reflete o local real da sua instância FastAPI

client = TestClient(app)


def test_fluxo_completo_usuario():
    # Email dinâmico para evitar o erro 400 de "E-mail já cadastrado" caso rode o teste várias vezes
    email_teste = f"teste_{random.randint(10000, 99999)}@exemplo.com"

    # 1. Criar (POST)
    novo_usuario = {
        "nome": "Usuario Teste",
        "email": email_teste,
        "telefone": 11999999999,  # Número inteiro
        "senha": "senha_segura_123",
        # 0 para comum (tudo em minúsculo, como esperado pelo banco)
        "usuario_tipo": 0
    }

    response_post = client.post("/usuarios/", json=novo_usuario)
    assert response_post.status_code == 201, f"Falha ao criar: {response_post.text}"

    # Extrai o ID gerado (que será um UUID retornado pelo banco)
    usuario_id = response_post.json()["id"]

    # 2. Buscar (GET)
    response_get = client.get(f"/usuarios/{usuario_id}")
    assert response_get.status_code == 200, f"Falha ao buscar: {response_get.text}"
    assert response_get.json()["email"] == email_teste

    # 3. Atualizar (PATCH)
    atualizacao = {"telefone": 11888888888}
    response_patch = client.patch(f"/usuarios/{usuario_id}", json=atualizacao)
    assert response_patch.status_code == 200, f"Falha ao atualizar: {response_patch.text}"
    assert response_patch.json()["telefone"] == 11888888888

    # 4. Deletar (DELETE)
    response_delete = client.delete(f"/usuarios/{usuario_id}")
    assert response_delete.status_code == 204, f"Falha ao deletar: {response_delete.text}"

    # 5. Confirmar Deleção (GET)
    response_confirm = client.get(f"/usuarios/{usuario_id}")
    assert response_confirm.status_code == 404, "O usuário ainda existe após a deleção."
