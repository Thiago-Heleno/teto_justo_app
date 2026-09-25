"""Testes unitários do serviço de tarefas."""

from datetime import datetime, timedelta, timezone
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
        "dificuldade": 2,
        "pontuacao": 20,
        "atraso_maximo": 5,
        "data_fim": "2026-10-01T12:00:00Z",
        "fk_casa_id": str(ids_relacionados["fk_casa_id"]),
        "fk_usuario_id": str(ids_relacionados["fk_usuario_id"]),
    }


def test_criar_tarefa_com_atribuicoes(
    servico, consulta, registro_tarefa, ids_relacionados
):
# A ordem esperada é: autorizar casa (retorna o dono), buscar em 'pertencer'
# os responsáveis informados, inserir tarefa, inserir atribuições e buscar
# as atribuições da resposta.
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
        peso=2,
        pontuacao=20,
        atraso_maximo=5,
        data_fim=datetime(2026, 10, 1, 12, tzinfo=timezone.utc),
        fk_casa_id=ids_relacionados["fk_casa_id"],
        fk_usuario_id=ids_relacionados["fk_usuario_id"],
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
        peso=1,
        pontuacao=10,
        atraso_maximo=5,
        data_fim=datetime(2026, 10, 1, tzinfo=timezone.utc),
        fk_casa_id=ids_relacionados["fk_casa_id"],
        fk_usuario_id=ids_relacionados["fk_usuario_id"],
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
            peso=1,
            pontuacao=10,
            atraso_maximo=5,
            data_fim=datetime(2026, 10, 1, tzinfo=timezone.utc),
            fk_casa_id=ids_relacionados["fk_casa_id"],
            fk_usuario_id=ids_relacionados["fk_usuario_id"],
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


def test_listar_tarefas_por_casa_combina_filtros(
    servico, consulta, id_tarefa, ids_relacionados
):
    segunda_tarefa = uuid4()
    responsavel = ids_relacionados["usuarios_atribuidos"][0]
    consulta.execute.return_value = SimpleNamespace(
        data=[{"id": str(id_tarefa)}, {"id": str(segunda_tarefa)}]
    )
    servico._montar_resposta = MagicMock(
        side_effect=[
            {
                "id": str(id_tarefa),
                "estado_atual": "pendente",
                "data_fim": (
                    datetime.now(timezone.utc) + timedelta(days=2)
                ).isoformat(),
                "usuarios_atribuidos": [str(responsavel)],
            },
            {
                "id": str(segunda_tarefa),
                "estado_atual": "finalizado",
                "data_fim": (
                    datetime.now(timezone.utc) + timedelta(days=2)
                ).isoformat(),
                "usuarios_atribuidos": [str(responsavel)],
            },
        ]
    )

    resultado = servico.listar_tarefas_por_casa(
        ids_relacionados["fk_casa_id"],
        estado="pendente",
        responsavel=responsavel,
        prazo="sete_dias",
    )

    assert [tarefa["id"] for tarefa in resultado] == [str(id_tarefa)]


def test_listar_tarefas_por_casa_filtra_prazos_atrasados(
    servico, consulta, ids_relacionados
):
    consulta.execute.return_value = SimpleNamespace(data=[{"id": "atrasada"}])
    servico._montar_resposta = MagicMock(
        return_value={
            "id": "atrasada",
            "estado_atual": "nao_feito",
            "data_fim": (
                datetime.now(timezone.utc) - timedelta(days=1)
            ).isoformat(),
            "usuarios_atribuidos": [],
        }
    )

    resultado = servico.listar_tarefas_por_casa(
        ids_relacionados["fk_casa_id"], prazo="atrasadas"
    )

    assert [tarefa["id"] for tarefa in resultado] == ["atrasada"]


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


def test_responsavel_pode_finalizar_a_propria_tarefa(
    servico, consulta, id_tarefa, registro_tarefa, ids_relacionados
):
    responsavel = ids_relacionados["usuarios_atribuidos"][0]
    finalizada = {**registro_tarefa, "estado_atual": "finalizado"}
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": str(responsavel)}]),
        SimpleNamespace(data=[finalizada]),
        SimpleNamespace(data=[finalizada]),
        SimpleNamespace(data=[{"fk_usuario_id": str(responsavel)}]),
    ]

    resultado = servico.atualizar_tarefa(
        id_tarefa,
        TarefaAtualizar(estado_atual="finalizado"),
        responsavel,
    )

    assert resultado["estado_atual"] == "finalizado"
    consulta.update.assert_called_once_with({"estado_atual": "finalizado"})


def test_nao_responsavel_nao_pode_finalizar_tarefa(
    servico, consulta, id_tarefa, registro_tarefa
):
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": str(uuid4())}]),
    ]

    with pytest.raises(HTTPException) as erro:
        servico.atualizar_tarefa(
            id_tarefa,
            TarefaAtualizar(estado_atual="finalizado"),
            uuid4(),
        )

    assert erro.value.status_code == 403
    consulta.update.assert_not_called()


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
        peso=1,
        pontuacao=10,
        atraso_maximo=5,
        data_fim=datetime(2026, 10, 1, tzinfo=timezone.utc),
        fk_casa_id=ids_relacionados["fk_casa_id"],
        fk_usuario_id=ids_relacionados["fk_usuario_id"],
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
        ("pontuacao", 15),
        ("atraso_maximo", 0),
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
        "pontuacao": 10,
        "atraso_maximo": 5,
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
        pontuacao=10,
        atraso_maximo=5,
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


def test_atualizar_tarefa_traduz_peso_para_dificuldade(
    servico, consulta, id_tarefa, registro_tarefa
):
    atualizado = {**registro_tarefa, "dificuldade": 3}

    # 1. Busca tarefa, 2. autoriza pela casa, 3. atualiza, 4. busca a tarefa
    # atualizada e 5. busca os usuários atribuídos.
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(
            data=[{"fk_usuario_id": registro_tarefa["fk_usuario_id"]}]
        ),
        SimpleNamespace(data=[atualizado]),
        SimpleNamespace(data=[atualizado]),
        SimpleNamespace(data=[]),
    ]

    resultado = servico.atualizar_tarefa(
        id_tarefa,
        TarefaAtualizar(peso=3),
        UUID(registro_tarefa["fk_usuario_id"]),
    )

    assert resultado["peso"] == 3
    consulta.update.assert_called_once_with({"dificuldade": 3})


def test_atualizar_tarefa_rejeita_responsaveis_duplicados(
    servico, consulta, id_tarefa, registro_tarefa
):
    usuario_repetido = uuid4()

    # 1. Busca tarefa, 2. autoriza pela casa. A duplicidade é detectada
    # antes de qualquer nova consulta ao banco.
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(
            data=[{"fk_usuario_id": registro_tarefa["fk_usuario_id"]}]
        ),
    ]

    with pytest.raises(HTTPException) as erro:
        servico.atualizar_tarefa(
            id_tarefa,
            TarefaAtualizar(usuarios_atribuidos=[usuario_repetido, usuario_repetido]),
            UUID(registro_tarefa["fk_usuario_id"]),
        )

    assert erro.value.status_code == 400
    consulta.delete.assert_not_called()


def test_atualizar_tarefa_rejeita_responsavel_de_outra_casa(
    servico, consulta, id_tarefa, registro_tarefa
):
    usuario_estranho = uuid4()

    # 1. Busca tarefa, 2. autoriza pela casa, 3. busca a casa (dono) e
    # 4. busca os vínculos 'pertencer' da casa para validar os responsáveis.
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(
            data=[{"fk_usuario_id": registro_tarefa["fk_usuario_id"]}]
        ),
        SimpleNamespace(
            data=[{"fk_usuario_id": registro_tarefa["fk_usuario_id"]}]
        ),
        SimpleNamespace(data=[]),
    ]

    with pytest.raises(HTTPException) as erro:
        servico.atualizar_tarefa(
            id_tarefa,
            TarefaAtualizar(usuarios_atribuidos=[usuario_estranho]),
            UUID(registro_tarefa["fk_usuario_id"]),
        )

    assert erro.value.status_code == 400
    consulta.delete.assert_not_called()


def test_atualizar_tarefa_aceita_dono_da_casa_como_responsavel(
    servico, consulta, id_tarefa, registro_tarefa
):
    dono_id = registro_tarefa["fk_usuario_id"]

    # 1. Busca tarefa, 2. autoriza pela casa, 3. busca a casa (dono),
    # 4. busca 'pertencer' da casa, 5. deleta atribuições antigas,
    # 6. insere a nova atribuição, 7. busca a tarefa atualizada e
    # 8. busca os usuários atribuídos.
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": dono_id}]),
        SimpleNamespace(data=[{"fk_usuario_id": dono_id}]),
        SimpleNamespace(data=[]),
        SimpleNamespace(data=[{"deleted": True}]),
        SimpleNamespace(
            data=[{"fk_usuario_id": dono_id, "fk_tarefa_id": registro_tarefa["id"]}]
        ),
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": dono_id}]),
    ]

    resultado = servico.atualizar_tarefa(
        id_tarefa,
        TarefaAtualizar(usuarios_atribuidos=[UUID(dono_id)]),
        UUID(dono_id),
    )

    assert resultado["usuarios_atribuidos"] == [dono_id]


def test_buscar_tarefa_expirada_vira_nao_feito(
    servico, consulta, registro_tarefa
):
    expirada = {
        **registro_tarefa,
        "estado_atual": "atrasada",
        "atraso_maximo": 5,
        "data_fim": "2020-01-01T00:00:00Z",
    }
    marcada_como_nao_feito = {**expirada, "estado_atual": "nao_feito"}

    # 1. Busca tarefa, 2. sincroniza o estado (atraso >= atraso_maximo) e
    # 3. busca os usuários atribuídos.
    consulta.execute.side_effect = [
        SimpleNamespace(data=[expirada]),
        SimpleNamespace(data=[marcada_como_nao_feito]),
        SimpleNamespace(data=[]),
    ]

    resultado = servico.buscar_tarefa(UUID(expirada["id"]))

    assert resultado["estado_atual"] == "nao_feito"
    consulta.update.assert_called_once_with({"estado_atual": "nao_feito"})


def test_buscar_tarefa_dentro_do_atraso_maximo_nao_muda_estado(
    servico, consulta, registro_tarefa
):
    agora = datetime.now(timezone.utc)
    dentro_do_prazo = {
        **registro_tarefa,
        "estado_atual": "atrasada",
        "atraso_maximo": 5,
        "data_fim": (agora - timedelta(days=1)).isoformat(),
    }

    # 1. Busca tarefa (atraso de 1 dia, dentro do atraso_maximo de 5) e
    # 2. busca os usuários atribuídos, sem sincronizar o estado.
    consulta.execute.side_effect = [
        SimpleNamespace(data=[dentro_do_prazo]),
        SimpleNamespace(data=[]),
    ]

    resultado = servico.buscar_tarefa(UUID(dentro_do_prazo["id"]))

    assert resultado["estado_atual"] == "atrasada"
    consulta.update.assert_not_called()


def test_buscar_tarefa_finalizada_nao_e_resincronizada(
    servico, consulta, registro_tarefa
):
    finalizada = {
        **registro_tarefa,
        "estado_atual": "finalizado",
        "atraso_maximo": 5,
        "data_fim": "2020-01-01T00:00:00Z",
    }

    # Estado já é final: nenhuma sincronização deve ocorrer, mesmo com o
    # prazo de atraso muito ultrapassado.
    consulta.execute.side_effect = [
        SimpleNamespace(data=[finalizada]),
        SimpleNamespace(data=[]),
    ]

    resultado = servico.buscar_tarefa(UUID(finalizada["id"]))

    assert resultado["estado_atual"] == "finalizado"
    consulta.update.assert_not_called()
