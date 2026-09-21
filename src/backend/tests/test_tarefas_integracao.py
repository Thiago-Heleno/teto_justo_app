from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core.database import get_supabase
from main import app


@pytest.fixture
def dependencias_temporarias(autenticacao_temporaria):
    supabase = get_supabase()
    marcador = uuid4().hex
    usuario_id = autenticacao_temporaria["usuario_id"]

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
    supabase.table("pertencer").delete().eq("fk_casa_id", casa_id).execute()
    supabase.table("casa").delete().eq("id", casa_id).execute()


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
                "estado_atual": "pendente",
                "peso": 2,
                "pontuacao": 20,
                "atraso_maximo": 5,
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
            json={"nome": novo_nome, "estado_atual": "atrasada", "peso": 4},
        )
        assert atualizada.status_code == 200, atualizada.text
        assert atualizada.json()["nome"] == novo_nome
        assert atualizada.json()["estado_atual"] == "atrasada"
        assert atualizada.json()["peso"] == 4

        # TESTE: Excluir
        excluida = cliente.delete(f"/tarefas/{tarefa['id']}")
        assert excluida.status_code == 200, excluida.text
        assert excluida.json() is True

        # TESTE: Garantir que foi excluída
        inexistente = cliente.get(f"/tarefas/{tarefa['id']}")
        assert inexistente.status_code == 404


def test_morador_nao_pode_criar_atualizar_ou_excluir_tarefa(
    dependencias_temporarias,
    autenticacao_temporaria,
    criar_autenticacao_temporaria,
):
    supabase = get_supabase()
    casa_id = dependencias_temporarias["casa_id"]
    administrador_id = autenticacao_temporaria["usuario_id"]
    morador = criar_autenticacao_temporaria()
    data_fim = datetime.now(timezone.utc) + timedelta(days=2)

    vinculo = (
        supabase.table("pertencer")
        .insert(
            {
                "fk_usuario_id": morador["usuario_id"],
                "fk_casa_id": casa_id,
                "score": 0,
            }
        )
        .execute()
    )
    assert vinculo.data

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=morador["headers"],
    ) as cliente_morador:
        proibida = cliente_morador.post(
            "/tarefas/",
            json={
                "nome": "Tarefa que o morador não pode criar",
                "estado_atual": "pendente",
                "peso": 1,
                "pontuacao": 10,
                "atraso_maximo": 5,
                "data_fim": data_fim.isoformat(),
                "fk_casa_id": casa_id,
                "fk_usuario_id": morador["usuario_id"],
            },
        )
        assert proibida.status_code == 403, proibida.text

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente_admin:
        criada = cliente_admin.post(
            "/tarefas/",
            json={
                "nome": "Tarefa protegida",
                "estado_atual": "pendente",
                "peso": 1,
                "pontuacao": 10,
                "atraso_maximo": 5,
                "data_fim": data_fim.isoformat(),
                "fk_casa_id": casa_id,
                "fk_usuario_id": administrador_id,
            },
        )
        assert criada.status_code == 201, criada.text
        tarefa = criada.json()

        troca_de_casa = cliente_admin.patch(
            f"/tarefas/{tarefa['id']}",
            json={"fk_casa_id": str(uuid4())},
        )
        assert troca_de_casa.status_code == 422, troca_de_casa.text

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=morador["headers"],
    ) as cliente_morador:
        atualizada = cliente_morador.patch(
            f"/tarefas/{tarefa['id']}",
            json={"nome": "Alteração proibida"},
        )
        assert atualizada.status_code == 403, atualizada.text

        excluida = cliente_morador.delete(f"/tarefas/{tarefa['id']}")
        assert excluida.status_code == 403, excluida.text

        preservada = cliente_morador.get(f"/tarefas/{tarefa['id']}")
        assert preservada.status_code == 200, preservada.text
        assert preservada.json()["nome"] == "Tarefa protegida"

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente_admin:
        excluida = cliente_admin.delete(f"/tarefas/{tarefa['id']}")
        assert excluida.status_code == 200, excluida.text


def test_criar_tarefa_rejeita_responsaveis_invalidos(
    dependencias_temporarias,
    autenticacao_temporaria,
    criar_autenticacao_temporaria,
):
    casa_id = dependencias_temporarias["casa_id"]
    administrador_id = autenticacao_temporaria["usuario_id"]
    morador_de_outra_casa = criar_autenticacao_temporaria()
    data_fim = datetime.now(timezone.utc) + timedelta(days=2)

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente_admin:
        # Responsável duplicado na mesma lista
        duplicado = cliente_admin.post(
            "/tarefas/",
            json={
                "nome": "Tarefa nascendo com responsável duplicado",
                "estado_atual": "pendente",
                "peso": 1,
                "pontuacao": 10,
                "atraso_maximo": 5,
                "data_fim": data_fim.isoformat(),
                "fk_casa_id": casa_id,
                "fk_usuario_id": administrador_id,
                "usuarios_atribuidos": [administrador_id, administrador_id],
            },
        )
        assert duplicado.status_code == 400, duplicado.text

        # Responsável que não pertence a esta casa
        de_outra_casa = cliente_admin.post(
            "/tarefas/",
            json={
                "nome": "Tarefa nascendo com responsável de outra casa",
                "estado_atual": "pendente",
                "peso": 1,
                "pontuacao": 10,
                "atraso_maximo": 5,
                "data_fim": data_fim.isoformat(),
                "fk_casa_id": casa_id,
                "fk_usuario_id": administrador_id,
                "usuarios_atribuidos": [morador_de_outra_casa["usuario_id"]],
            },
        )
        assert de_outra_casa.status_code == 400, de_outra_casa.text

        # Responsável válido (o próprio dono da casa) passa normalmente
        valida = cliente_admin.post(
            "/tarefas/",
            json={
                "nome": "Tarefa nascendo com responsável válido",
                "estado_atual": "pendente",
                "peso": 1,
                "pontuacao": 10,
                "atraso_maximo": 5,
                "data_fim": data_fim.isoformat(),
                "fk_casa_id": casa_id,
                "fk_usuario_id": administrador_id,
                "usuarios_atribuidos": [administrador_id],
            },
        )
        assert valida.status_code == 201, valida.text
        assert valida.json()["usuarios_atribuidos"] == [administrador_id]


def test_atualizar_tarefa_rejeita_responsaveis_invalidos(
    dependencias_temporarias,
    autenticacao_temporaria,
    criar_autenticacao_temporaria,
):
    supabase = get_supabase()
    casa_id = dependencias_temporarias["casa_id"]
    administrador_id = autenticacao_temporaria["usuario_id"]
    morador_da_casa = criar_autenticacao_temporaria()
    morador_de_outra_casa = criar_autenticacao_temporaria()
    data_fim = datetime.now(timezone.utc) + timedelta(days=2)

    vinculo = (
        supabase.table("pertencer")
        .insert(
            {
                "fk_usuario_id": morador_da_casa["usuario_id"],
                "fk_casa_id": casa_id,
                "score": 0,
            }
        )
        .execute()
    )
    assert vinculo.data

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente_admin:
        criada = cliente_admin.post(
            "/tarefas/",
            json={
                "nome": "Tarefa com responsáveis a validar",
                "estado_atual": "pendente",
                "peso": 1,
                "pontuacao": 10,
                "atraso_maximo": 5,
                "data_fim": data_fim.isoformat(),
                "fk_casa_id": casa_id,
                "fk_usuario_id": administrador_id,
            },
        )
        assert criada.status_code == 201, criada.text
        tarefa = criada.json()

        # Responsável duplicado na mesma lista
        duplicado = cliente_admin.patch(
            f"/tarefas/{tarefa['id']}",
            json={
                "usuarios_atribuidos": [
                    morador_da_casa["usuario_id"],
                    morador_da_casa["usuario_id"],
                ]
            },
        )
        assert duplicado.status_code == 400, duplicado.text

        # Responsável que não pertence a esta casa
        de_outra_casa = cliente_admin.patch(
            f"/tarefas/{tarefa['id']}",
            json={"usuarios_atribuidos": [morador_de_outra_casa["usuario_id"]]},
        )
        assert de_outra_casa.status_code == 400, de_outra_casa.text

        # Responsáveis válidos: morador vinculado à casa e o próprio administrador
        validos = cliente_admin.patch(
            f"/tarefas/{tarefa['id']}",
            json={
                "usuarios_atribuidos": [
                    morador_da_casa["usuario_id"],
                    administrador_id,
                ]
            },
        )
        assert validos.status_code == 200, validos.text
        assert set(validos.json()["usuarios_atribuidos"]) == {
            morador_da_casa["usuario_id"],
            administrador_id,
        }


def test_tarefa_expirada_vira_nao_feito_ao_ser_consultada(
    dependencias_temporarias,
    autenticacao_temporaria,
):
    casa_id = dependencias_temporarias["casa_id"]
    usuario_id = dependencias_temporarias["usuario_id"]
    # data_fim já passou há mais dias do que o atraso_maximo (2): a tarefa
    # nunca foi finalizada manualmente e deve virar 'nao_feito' sozinha
    # na primeira consulta, sem nenhum job/cron envolvido.
    data_fim = datetime.now(timezone.utc) - timedelta(days=10)

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente:
        criada = cliente.post(
            "/tarefas/",
            json={
                "nome": "Tarefa vencida",
                "estado_atual": "atrasada",
                "peso": 1,
                "pontuacao": 10,
                "atraso_maximo": 2,
                "data_fim": data_fim.isoformat(),
                "fk_casa_id": casa_id,
                "fk_usuario_id": usuario_id,
            },
        )
        assert criada.status_code == 201, criada.text
        tarefa = criada.json()

        consultada = cliente.get(f"/tarefas/{tarefa['id']}")
        assert consultada.status_code == 200, consultada.text
        assert consultada.json()["estado_atual"] == "nao_feito"
