"""Testes unitários do serviço de tarefas."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from schemas.tarefa import TarefaAtualizar, TarefaCriar
from services.tarefa import ServicoTarefa


@pytest.fixture
def consulta():
    consulta = MagicMock()
    consulta.insert.return_value = consulta
    consulta.select.return_value = consulta
    consulta.eq.return_value = consulta
    consulta.in_.return_value = consulta
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
        "estado_atual": "pendente",
        "data_fim": "2026-10-01T12:00:00Z",
        "fk_casa_id": str(ids_relacionados["fk_casa_id"]),
        "fk_usuario_id": str(ids_relacionados["fk_usuario_id"]),
    }


def test_criar_tarefa_com_atribuicoes(
    servico, consulta, registro_tarefa, ids_relacionados
):
# A ordem esperada é: autorizar casa, inserir tarefa, inserir atribuições
# e buscar as atribuições da resposta.
    consulta.execute.side_effect = [
        SimpleNamespace(
            data=[{"fk_usuario_id": str(ids_relacionados["fk_usuario_id"])}]
        ),
        SimpleNamespace(
            data=[
                {"fk_usuario_id": str(id_usuario)}
                for id_usuario in ids_relacionados["usuarios_atribuidos"]
            ]
        ),
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": str(u), "fk_tarefa_id": str(registro_tarefa["id"])}
                              for u in ids_relacionados["usuarios_atribuidos"]]
                        ),
        SimpleNamespace(data=[{"fk_usuario_id": str(u)}
                              for u in ids_relacionados["usuarios_atribuidos"]]
                        )
    ]

    dados = TarefaCriar(
        nome="Lavar a louça",
        descricao="Lavar e secar a louça do jantar",
        estado_atual="pendente",
        data_fim=datetime(2026, 10, 1, 12, tzinfo=timezone.utc),
        fk_casa_id=ids_relacionados["fk_casa_id"],
        fk_usuario_id=ids_relacionados["fk_usuario_id"],
        peso=1,
        usuarios_atribuidos=ids_relacionados["usuarios_atribuidos"],
    )

    resultado = servico.criar_tarefa(
        dados,
        ids_relacionados["fk_usuario_id"],
    )

    assert resultado["id"] == registro_tarefa["id"]
    assert len(resultado["usuarios_atribuidos"]) == 2
    assert consulta.insert.call_count == 2 # Uma para tarefa, outra para a tabela relacional


def test_criar_tarefa_sem_retorno_do_banco_gera_500(servico, consulta, ids_relacionados):
    consulta.execute.side_effect = [
        SimpleNamespace(
            data=[{"fk_usuario_id": str(ids_relacionados["fk_usuario_id"])}]
        ),
        SimpleNamespace(
            data=[
                {"fk_usuario_id": str(id_usuario)}
                for id_usuario in ids_relacionados["usuarios_atribuidos"]
            ]
        ),
        SimpleNamespace(data=[]),
    ]
    dados = TarefaCriar(
        nome="Tarefa falha",
        estado_atual="pendente",
        data_fim=datetime(2026, 10, 1, tzinfo=timezone.utc),
        fk_casa_id=ids_relacionados["fk_casa_id"],
        fk_usuario_id=ids_relacionados["fk_usuario_id"],
        peso=1,
        usuarios_atribuidos=ids_relacionados["usuarios_atribuidos"],
    )

    with pytest.raises(HTTPException) as erro:
        servico.criar_tarefa(
            dados,
            ids_relacionados["fk_usuario_id"],
        )

    assert erro.value.status_code == 500
    assert erro.value.detail == "Erro ao criar tarefa no banco."


@pytest.mark.parametrize("estado_invalido", [0, "em_andamento"])
def test_criar_tarefa_rejeita_estado_fora_do_contrato(
    estado_invalido, ids_relacionados
):
    with pytest.raises(ValidationError):
        TarefaCriar(
            nome="Tarefa inválida",
            estado_atual=estado_invalido,
            data_fim=datetime(2026, 10, 1, tzinfo=timezone.utc),
            fk_casa_id=ids_relacionados["fk_casa_id"],
            fk_usuario_id=ids_relacionados["fk_usuario_id"],
            peso=1,
            usuarios_atribuidos=ids_relacionados["usuarios_atribuidos"],
        )


def test_atualizar_tarefa_rejeita_troca_de_casa():
    with pytest.raises(ValidationError):
        TarefaAtualizar(fk_casa_id=uuid4())


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

# 1. Busca tarefa, 2. autoriza pela casa, 3. atualiza, 4. busca a tarefa
# atualizada e 5. busca os usuários atribuídos.
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(
            data=[{"fk_usuario_id": registro_tarefa["fk_usuario_id"]}]
        ),
        SimpleNamespace(data=[atualizado]),
        SimpleNamespace(data=[atualizado]),
        SimpleNamespace(data=[])
    ]

    resultado = servico.atualizar_tarefa(
        id_tarefa,
        TarefaAtualizar(nome="Novo nome"),
        UUID(registro_tarefa["fk_usuario_id"]),
    )

    assert resultado["nome"] == "Novo nome"
    consulta.update.assert_called_once_with({"nome": "Novo nome"})


def test_excluir_tarefa_existente_retorna_true(
    servico, consulta, id_tarefa, registro_tarefa
):
    # 1. Busca tarefa, 2. autoriza pela casa, 3. deleta de 'atribuida'
    # e 4. deleta de 'tarefa'.
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(
            data=[{"fk_usuario_id": registro_tarefa["fk_usuario_id"]}]
        ),
        SimpleNamespace(data=[{"deleted": True}]),
        SimpleNamespace(data=[registro_tarefa])
    ]

    resultado = servico.excluir_tarefa(
        id_tarefa,
        UUID(registro_tarefa["fk_usuario_id"]),
    )

    assert resultado is True
    assert consulta.delete.call_count == 2


def test_morador_nao_pode_criar_tarefa(
    servico, consulta, ids_relacionados
):
    consulta.execute.return_value = SimpleNamespace(
        data=[{"fk_usuario_id": str(uuid4())}]
    )
    dados = TarefaCriar(
        nome="Tarefa proibida",
        estado_atual="pendente",
        data_fim=datetime(2026, 10, 1, tzinfo=timezone.utc),
        fk_casa_id=ids_relacionados["fk_casa_id"],
        fk_usuario_id=ids_relacionados["fk_usuario_id"],
        peso=1,
        usuarios_atribuidos=ids_relacionados["usuarios_atribuidos"],
    )

    with pytest.raises(HTTPException) as erro:
        servico.criar_tarefa(dados, ids_relacionados["fk_usuario_id"])

    assert erro.value.status_code == 403
    consulta.insert.assert_not_called()


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("peso", 0),
        ("usuarios_atribuidos", []),
        ("data_fim", datetime(2020, 1, 1, tzinfo=timezone.utc)),
    ],
)
def test_criar_tarefa_rejeita_requisitos_invalidos(campo, valor, ids_relacionados):
    dados = {
        "nome": "Tarefa inválida",
        "estado_atual": "pendente",
        "data_fim": datetime(2026, 10, 1, tzinfo=timezone.utc),
        "fk_casa_id": ids_relacionados["fk_casa_id"],
        "fk_usuario_id": ids_relacionados["fk_usuario_id"],
        "peso": 1,
        "usuarios_atribuidos": [ids_relacionados["fk_usuario_id"]],
    }
    dados[campo] = valor

    with pytest.raises(ValidationError):
        TarefaCriar(**dados)


def test_criar_tarefa_rejeita_responsavel_de_outra_casa(
    servico, consulta, ids_relacionados
):
    consulta.execute.side_effect = [
        SimpleNamespace(
            data=[{"fk_usuario_id": str(ids_relacionados["fk_usuario_id"])}]
        ),
        SimpleNamespace(data=[]),
    ]
    dados = TarefaCriar(
        nome="Tarefa inválida",
        estado_atual="pendente",
        data_fim=datetime(2026, 10, 1, tzinfo=timezone.utc),
        fk_casa_id=ids_relacionados["fk_casa_id"],
        fk_usuario_id=ids_relacionados["fk_usuario_id"],
        peso=1,
        usuarios_atribuidos=[uuid4()],
    )

    with pytest.raises(HTTPException) as erro:
        servico.criar_tarefa(dados, ids_relacionados["fk_usuario_id"])

    assert erro.value.status_code == 422
    consulta.insert.assert_not_called()


def test_morador_nao_pode_atualizar_tarefa(
    servico, consulta, id_tarefa, registro_tarefa
):
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": str(uuid4())}]),
    ]

    with pytest.raises(HTTPException) as erro:
        servico.atualizar_tarefa(
            id_tarefa,
            TarefaAtualizar(nome="Alteração proibida"),
            UUID(registro_tarefa["fk_usuario_id"]),
        )

    assert erro.value.status_code == 403
    consulta.update.assert_not_called()


def test_morador_nao_pode_excluir_tarefa(
    servico, consulta, id_tarefa, registro_tarefa
):
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": str(uuid4())}]),
    ]

    with pytest.raises(HTTPException) as erro:
        servico.excluir_tarefa(
            id_tarefa,
            UUID(registro_tarefa["fk_usuario_id"]),
        )

    assert erro.value.status_code == 403
    consulta.delete.assert_not_called()
