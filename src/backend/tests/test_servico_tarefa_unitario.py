"""Testes unitários do serviço de tarefas."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from schemas.tarefa import TarefaAtualizar, TarefaCriar
from services.tarefa import ServicoTarefa


@pytest.fixture
def consulta():
    consulta = MagicMock()
    consulta.insert.return_value = consulta
    consulta.select.return_value = consulta
    consulta.eq.return_value = consulta
    consulta.range.return_value = consulta
    consulta.update.return_value = consulta
    consulta.delete.return_value = consulta
    return consulta


@pytest.fixture
def banco(consulta):
    banco = MagicMock()
    banco.table.return_value = consulta
    return banco


@pytest.fixture
def servico(banco):
    return ServicoTarefa(banco)


@pytest.fixture
def id_tarefa():
    return uuid4()


@pytest.fixture
def ids_relacionados():
    return {
        "fk_casa_id": uuid4(),
        "fk_usuario_id": uuid4(),
        "usuarios_atribuidos": [uuid4(), uuid4()]
    }


@pytest.fixture
def registro_tarefa(id_tarefa, ids_relacionados):
    return {
        "id": str(id_tarefa),
        "nome": "Lavar a louça",
        "descricao": "Lavar e secar a louça do jantar",
        "estado_atual": 0,
        "data_fim": "2026-10-01T12:00:00Z",
        "fk_casa_id": str(ids_relacionados["fk_casa_id"]),
        "fk_usuario_id": str(ids_relacionados["fk_usuario_id"]),
    }


def test_criar_tarefa_com_atribuicoes(
    servico, consulta, registro_tarefa, ids_relacionados
):
    # A ordem de execução esperada é: insert (tarefa), insert (atribuida), select (buscar atribuicoes)
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": str(u), "fk_tarefa_id": str(registro_tarefa["id"])} for u in ids_relacionados["usuarios_atribuidos"]]),
        SimpleNamespace(data=[{"fk_usuario_id": str(u)} for u in ids_relacionados["usuarios_atribuidos"]])
    ]
    
    dados = TarefaCriar(
        nome="Lavar a louça",
        descricao="Lavar e secar a louça do jantar",
        estado_atual=0,
        data_fim=datetime(2026, 10, 1, 12, tzinfo=timezone.utc),
        fk_casa_id=ids_relacionados["fk_casa_id"],
        fk_usuario_id=ids_relacionados["fk_usuario_id"],
        usuarios_atribuidos=ids_relacionados["usuarios_atribuidos"],
    )

    resultado = servico.criar_tarefa(dados)

    assert resultado["id"] == registro_tarefa["id"]
    assert len(resultado["usuarios_atribuidos"]) == 2
    assert consulta.insert.call_count == 2 # Uma para tarefa, outra para a tabela relacional


def test_criar_tarefa_sem_retorno_do_banco_gera_500(servico, consulta, ids_relacionados):
    consulta.execute.return_value = SimpleNamespace(data=[])
    dados = TarefaCriar(
        nome="Tarefa falha",
        estado_atual=0,
        data_fim=datetime(2026, 10, 1, tzinfo=timezone.utc),
        fk_casa_id=ids_relacionados["fk_casa_id"],
        fk_usuario_id=ids_relacionados["fk_usuario_id"],
    )

    with pytest.raises(HTTPException) as erro:
        servico.criar_tarefa(dados)

    assert erro.value.status_code == 500
    assert erro.value.detail == "Erro ao criar tarefa no banco."


def test_buscar_tarefa_por_id(servico, consulta, id_tarefa, registro_tarefa):
    # 1. Busca a tarefa bruta, 2. Busca os usuários atribuídos
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": str(uuid4())}])
    ]

    resultado = servico.buscar_tarefa(id_tarefa)

    assert resultado["id"] == registro_tarefa["id"]
    assert len(resultado["usuarios_atribuidos"]) == 1
    assert consulta.select.call_count == 2


def test_atualizar_tarefa_envia_apenas_campos_informados(
    servico, consulta, id_tarefa, registro_tarefa
):
    atualizado = {**registro_tarefa, "nome": "Novo nome"}
    
    # 1. Busca tarefa para ver se existe, 2. Update da tarefa, 3. Busca tarefa atualizada, 4. Busca atribuidos
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[atualizado]),
        SimpleNamespace(data=[atualizado]),
        SimpleNamespace(data=[])
    ]

    resultado = servico.atualizar_tarefa(
        id_tarefa,
        TarefaAtualizar(nome="Novo nome"),
    )

    assert resultado["nome"] == "Novo nome"
    consulta.update.assert_called_once_with({"nome": "Novo nome"})


def test_excluir_tarefa_existente_retorna_true(
    servico, consulta, id_tarefa, registro_tarefa
):
    # 1. Busca tarefa bruta (confirma que existe)
    # 2. Deleta de 'atribuida'
    # 3. Deleta de 'tarefa'
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[{"deleted": True}]),
        SimpleNamespace(data=[registro_tarefa])
    ]

    resultado = servico.excluir_tarefa(id_tarefa)

    assert resultado is True
    assert consulta.delete.call_count == 2