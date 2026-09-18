from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core.database import get_supabase
from main import app


@pytest.fixture
def dependencias_temporarias():
    supabase = get_supabase()
    marcador = uuid4().hex

    # 1. Criar usuário temporário
    res_usuario = (
        supabase.table("usuario")
        .insert({
            "nome": "Usuário Teste Tarefa",
            "email": f"teste-tarefa-{marcador}@example.com",
            "senha_hash": "hash-falso",
            "usuario_tipo": 0,
        })
        .execute()
    )
    usuario_id = res_usuario.data[0]["id"]

    # 2. Criar casa temporária
    res_casa = (
        supabase.table("casa")
        .insert({
            "nome": f"Casa Teste {marcador}",
            "fk_usuario_id": usuario_id
        })
        .execute()
    )
    casa_id = res_casa.data[0]["id"]

    yield {"usuario_id": usuario_id, "casa_id": casa_id}

    # Limpeza (Teardown)
    supabase.table("tarefa").delete().eq("fk_casa_id", casa_id).execute()
    supabase.table("casa").delete().eq("id", casa_id).execute()
    supabase.table("usuario").delete().eq("id", usuario_id).execute()


def test_crud_tarefa_no_supabase(
    dependencias_temporarias,
    autenticacao_temporaria,
):
    usuario_id = dependencias_temporarias["usuario_id"]
    casa_id = dependencias_temporarias["casa_id"]
    data_fim = datetime.now(timezone.utc) + timedelta(days=2)

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente:
        # TESTE: Criar
        criada = cliente.post(
            "/tarefas/",
            json={
                "nome": "Limpar a caixa de areia",
                "descricao": "Usar a pá nova",
                "estado_atual": 0,
                "data_fim": data_fim.isoformat(),
                "fk_casa_id": casa_id,
                "fk_usuario_id": usuario_id,
                "usuarios_atribuidos": [usuario_id]
            },
        )
        assert criada.status_code == 201, criada.text
        tarefa = criada.json()
        assert tarefa["nome"] == "Limpar a caixa de areia"
        assert tarefa["fk_casa_id"] == casa_id
        assert len(tarefa["usuarios_atribuidos"]) == 1

        # TESTE: Buscar por ID
        encontrada = cliente.get(f"/tarefas/{tarefa['id']}")
        assert encontrada.status_code == 200, encontrada.text
        assert encontrada.json()["id"] == tarefa["id"]

        # TESTE: Listar por casa
        lista_casa = cliente.get(f"/tarefas/casa/{casa_id}")
        assert lista_casa.status_code == 200, lista_casa.text
        assert len(lista_casa.json()) >= 1

        # TESTE: Atualizar
        novo_nome = "Limpar toda a varanda"
        atualizada = cliente.patch(
            f"/tarefas/{tarefa['id']}",
            json={"nome": novo_nome, "estado_atual": 1},
        )
        assert atualizada.status_code == 200, atualizada.text
        assert atualizada.json()["nome"] == novo_nome
        assert atualizada.json()["estado_atual"] == 1

        # TESTE: Excluir
        excluida = cliente.delete(f"/tarefas/{tarefa['id']}")
        assert excluida.status_code == 200, excluida.text
        assert excluida.json() is True

        # TESTE: Garantir que foi excluída
        inexistente = cliente.get(f"/tarefas/{tarefa['id']}")
        assert inexistente.status_code == 404
