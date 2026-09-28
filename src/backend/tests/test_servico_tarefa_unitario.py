"""Testes unitários do serviço de tarefas."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from postgrest.exceptions import APIError

from schemas.tarefa import TarefaAtualizar, TarefaCriar, TarefaResposta
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
    return {"fk_casa_id": uuid4(), "fk_usuario_id": uuid4(), "usuarios_atribuidos": [uuid4()]}


@pytest.fixture
def registro_tarefa(id_tarefa, ids_relacionados):
    return {
        "id": str(id_tarefa),
        "nome": "Lavar a louça",
        "descricao": "Lavar e secar a louça do jantar",
        "estado_atual": "pendente",
        "dificuldade": 2,
        "pontuacao": 25,
        "atraso_maximo": 5,
        "data_fim": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
        "fk_casa_id": str(ids_relacionados["fk_casa_id"]),
        "fk_usuario_id": str(ids_relacionados["fk_usuario_id"]),
    }


def test_criar_tarefa_com_atribuicoes(servico, consulta, registro_tarefa, ids_relacionados):
    # A ordem esperada é: autorizar casa (retorna o dono), buscar em 'pertencer'
    # os responsáveis informados, inserir tarefa, inserir atribuições e buscar
    # as atribuições da resposta.
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"fk_usuario_id": str(ids_relacionados["fk_usuario_id"])}]),
        SimpleNamespace(
            data=[
                {"fk_usuario_id": str(id_usuario)}
                for id_usuario in ids_relacionados["usuarios_atribuidos"]
            ]
        ),
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(
            data=[
                {"fk_usuario_id": str(u), "fk_tarefa_id": str(registro_tarefa["id"])}
                for u in ids_relacionados["usuarios_atribuidos"]
            ]
        ),
        SimpleNamespace(
            data=[{"fk_usuario_id": str(u)} for u in ids_relacionados["usuarios_atribuidos"]]
        ),
    ]

    dados = TarefaCriar(
        nome="Lavar a louça",
        descricao="Lavar e secar a louça do jantar",
        estado_atual="pendente",
        peso=2,
        atraso_maximo=5,
        prazo_dias=3,
        fk_casa_id=ids_relacionados["fk_casa_id"],
        usuarios_atribuidos=ids_relacionados["usuarios_atribuidos"],
    )

    resultado = servico.criar_tarefa(
        dados,
        ids_relacionados["fk_usuario_id"],
    )

    assert resultado["id"] == registro_tarefa["id"]
    assert len(resultado["usuarios_atribuidos"]) == 1
    gravada = consulta.insert.call_args_list[0].args[0]
    inicio = datetime.fromisoformat(gravada["data_inicio"])
    fim = datetime.fromisoformat(gravada["data_fim"])
    assert datetime.now(timezone.utc) - timedelta(seconds=5) <= inicio <= datetime.now(timezone.utc)
    assert fim - inicio == timedelta(days=3)
    assert gravada["pontuacao"] == 25
    assert gravada["fk_usuario_id"] == str(ids_relacionados["fk_usuario_id"])
    assert "estrategia_penalidade" not in gravada
    TarefaResposta.model_validate(resultado)
    assert consulta.insert.call_count == 2  # Uma para tarefa, outra para a tabela relacional


def test_criar_tarefa_sem_retorno_do_banco_gera_500(servico, consulta, ids_relacionados):
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"fk_usuario_id": str(ids_relacionados["fk_usuario_id"])}]),
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
        atraso_maximo=5,
        prazo_dias=3,
        fk_casa_id=ids_relacionados["fk_casa_id"],
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
def test_criar_tarefa_rejeita_estado_fora_do_contrato(estado_invalido, ids_relacionados):
    with pytest.raises(ValidationError):
        TarefaCriar(
            nome="Tarefa inválida",
            estado_atual=estado_invalido,
            peso=1,
            atraso_maximo=5,
            prazo_dias=3,
            fk_casa_id=ids_relacionados["fk_casa_id"],
            usuarios_atribuidos=ids_relacionados["usuarios_atribuidos"],
        )


def test_atualizar_tarefa_rejeita_troca_de_casa():
    with pytest.raises(ValidationError):
        TarefaAtualizar(fk_casa_id=uuid4())


def test_buscar_tarefa_por_id(servico, consulta, id_tarefa, registro_tarefa):
    # 1. Busca a tarefa bruta, 2. Busca os usuários atribuídos
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": str(uuid4())}]),
    ]

    resultado = servico.buscar_tarefa(id_tarefa)

    assert resultado["id"] == registro_tarefa["id"]
    assert len(resultado["usuarios_atribuidos"]) == 1
    assert consulta.select.call_count == 2


def test_listar_tarefas_por_casa_combina_filtros(servico, consulta, id_tarefa, ids_relacionados):
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
                "data_fim": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
                "usuarios_atribuidos": [str(responsavel)],
            },
            {
                "id": str(segunda_tarefa),
                "estado_atual": "finalizado",
                "data_fim": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
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


def test_listar_tarefas_por_casa_filtra_prazos_atrasados(servico, consulta, ids_relacionados):
    consulta.execute.return_value = SimpleNamespace(data=[{"id": "atrasada"}])
    servico._montar_resposta = MagicMock(
        return_value={
            "id": "atrasada",
            "estado_atual": "nao_feito",
            "data_fim": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "usuarios_atribuidos": [],
        }
    )

    resultado = servico.listar_tarefas_por_casa(ids_relacionados["fk_casa_id"], prazo="atrasadas")

    assert [tarefa["id"] for tarefa in resultado] == ["atrasada"]


def test_atualizar_tarefa_envia_apenas_campos_informados(
    servico, consulta, id_tarefa, registro_tarefa
):
    atualizado = {**registro_tarefa, "nome": "Novo nome"}

    # 1. Busca tarefa, 2. autoriza pela casa, 3. atualiza, 4. busca a tarefa
    # atualizada e 5. busca os usuários atribuídos.
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": registro_tarefa["fk_usuario_id"]}]),
        SimpleNamespace(data=[atualizado]),
        SimpleNamespace(data=[atualizado]),
        SimpleNamespace(data=[]),
    ]

    resultado = servico.atualizar_tarefa(
        id_tarefa,
        TarefaAtualizar(nome="Novo nome"),
        UUID(registro_tarefa["fk_usuario_id"]),
    )

    assert resultado["nome"] == "Novo nome"
    consulta.update.assert_called_once_with({"nome": "Novo nome"})


@pytest.mark.parametrize("horas_atraso,pontos", [(-1, 50), (12, 33), (36, 17)])
def test_responsavel_finaliza_com_pontos_calculados_no_backend(
    servico,
    banco,
    consulta,
    id_tarefa,
    registro_tarefa,
    ids_relacionados,
    monkeypatch,
    horas_atraso,
    pontos,
):
    agora = datetime(2030, 1, 10, tzinfo=timezone.utc)

    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):
            return agora

    monkeypatch.setattr("services.tarefa.datetime", Relogio)
    responsavel = ids_relacionados["usuarios_atribuidos"][0]
    tarefa = {
        **registro_tarefa,
        "dificuldade": 3,
        "atraso_maximo": 2,
        "data_fim": (agora - timedelta(hours=horas_atraso)).isoformat(),
    }
    finalizada = {
        **tarefa,
        "estado_atual": "finalizado",
        "concluida_em": agora.isoformat(),
        "resultado_pontuacao": {
            "pontos_possiveis": 50,
            "pontos_ganhos": pontos,
            "saldo_atual": 100 + pontos,
        },
    }
    consulta.execute.side_effect = [
        SimpleNamespace(data=[tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": str(responsavel)}]),
        SimpleNamespace(data=[{"fk_usuario_id": str(responsavel)}]),
    ]
    banco.rpc.return_value.execute.return_value = SimpleNamespace(data=finalizada)

    resultado = servico.atualizar_tarefa(
        id_tarefa,
        TarefaAtualizar(estado_atual="finalizado"),
        responsavel,
    )

    assert resultado["estado_atual"] == "finalizado"
    assert resultado["resultado_pontuacao"] == finalizada["resultado_pontuacao"]
    assert resultado["concluida_em"] == agora.isoformat()
    TarefaResposta.model_validate(resultado)
    banco.rpc.assert_called_once_with(
        "registrar_conclusao_tarefa",
        {
            "p_id_tarefa": str(id_tarefa),
            "p_id_usuario": str(responsavel),
            "p_pontos": pontos,
            "p_concluida_em": agora.isoformat(),
            "p_dificuldade": 3,
            "p_atraso_maximo": 2,
            "p_data_fim": tarefa["data_fim"],
            "p_data_inicio": None,
            "p_id_casa": tarefa["fk_casa_id"],
        },
    )
    consulta.update.assert_not_called()
    consulta.insert.assert_not_called()


def test_nao_responsavel_nao_pode_finalizar_tarefa(servico, consulta, id_tarefa, registro_tarefa):
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


def test_endpoint_de_conclusao_usa_responsavel_e_persistencia_atomica(
    servico, banco, consulta, id_tarefa, registro_tarefa, ids_relacionados
):
    agora = datetime.now(timezone.utc)
    tarefa = {
        **registro_tarefa,
        "data_fim": (agora + timedelta(days=1)).isoformat(),
    }
    responsavel = ids_relacionados["usuarios_atribuidos"][0]
    finalizada = {
        **tarefa,
        "estado_atual": "finalizado",
        "concluida_em": agora.isoformat(),
        "resultado_pontuacao": {
            "pontos_possiveis": 25,
            "pontos_ganhos": 25,
            "saldo_atual": 25,
        },
    }
    consulta.execute.side_effect = [
        SimpleNamespace(data=[tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": str(responsavel)}]),
        SimpleNamespace(data=[{"fk_usuario_id": str(responsavel)}]),
    ]
    banco.rpc.return_value.execute.return_value = SimpleNamespace(data=finalizada)

    resultado = servico.concluir_tarefa(id_tarefa, responsavel)

    assert resultado["estado_atual"] == "finalizado"
    assert resultado["resultado_pontuacao"]["pontos_ganhos"] == 25
    banco.rpc.assert_called_once()
    nome_rpc, parametros = banco.rpc.call_args.args
    assert nome_rpc == "registrar_conclusao_tarefa"
    concluida_em = parametros.pop("p_concluida_em")
    assert parametros == {
        "p_id_tarefa": str(id_tarefa),
        "p_id_usuario": str(responsavel),
        "p_pontos": 25,
        "p_dificuldade": tarefa["dificuldade"],
        "p_atraso_maximo": tarefa["atraso_maximo"],
        "p_data_fim": tarefa["data_fim"],
        "p_data_inicio": tarefa.get("data_inicio"),
        "p_id_casa": tarefa["fk_casa_id"],
    }
    assert datetime.fromisoformat(concluida_em).tzinfo == timezone.utc
    consulta.update.assert_not_called()
    consulta.insert.assert_not_called()


def test_endpoint_de_conclusao_rejeita_nao_responsavel(
    servico, banco, consulta, id_tarefa, registro_tarefa
):
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": str(uuid4())}]),
    ]

    with pytest.raises(HTTPException) as erro:
        servico.concluir_tarefa(id_tarefa, uuid4())

    assert erro.value.status_code == 403
    banco.rpc.assert_not_called()


def test_excluir_tarefa_existente_retorna_true(servico, consulta, id_tarefa, registro_tarefa):
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": registro_tarefa["fk_usuario_id"]}]),
    ]
    servico.supabase.rpc.return_value.execute.return_value = SimpleNamespace(data=True)

    resultado = servico.excluir_tarefa(
        id_tarefa,
        UUID(registro_tarefa["fk_usuario_id"]),
    )

    assert resultado is True
    servico.supabase.rpc.assert_called_once_with(
        "excluir_tarefa_sem_credito", {"p_id_tarefa": str(id_tarefa)}
    )
    consulta.delete.assert_not_called()


def test_morador_nao_pode_criar_tarefa(servico, consulta, ids_relacionados):
    consulta.execute.return_value = SimpleNamespace(data=[{"fk_usuario_id": str(uuid4())}])
    dados = TarefaCriar(
        nome="Tarefa proibida",
        estado_atual="pendente",
        peso=1,
        atraso_maximo=5,
        prazo_dias=3,
        fk_casa_id=ids_relacionados["fk_casa_id"],
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
        ("prazo_dias", 0),
    ],
)
def test_criar_tarefa_rejeita_requisitos_invalidos(campo, valor, ids_relacionados):
    dados = {
        "nome": "Tarefa inválida",
        "estado_atual": "pendente",
        "prazo_dias": 3,
        "fk_casa_id": ids_relacionados["fk_casa_id"],
        "peso": 1,
        "atraso_maximo": 5,
        "usuarios_atribuidos": [ids_relacionados["fk_usuario_id"]],
    }
    dados[campo] = valor

    with pytest.raises(ValidationError):
        TarefaCriar(**dados)


def test_criar_tarefa_rejeita_responsavel_de_outra_casa(servico, consulta, ids_relacionados):
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"fk_usuario_id": str(ids_relacionados["fk_usuario_id"])}]),
        SimpleNamespace(data=[]),
    ]
    dados = TarefaCriar(
        nome="Tarefa inválida",
        estado_atual="pendente",
        prazo_dias=3,
        fk_casa_id=ids_relacionados["fk_casa_id"],
        peso=1,
        atraso_maximo=5,
        usuarios_atribuidos=[uuid4()],
    )

    with pytest.raises(HTTPException) as erro:
        servico.criar_tarefa(dados, ids_relacionados["fk_usuario_id"])

    assert erro.value.status_code == 422
    consulta.insert.assert_not_called()


def test_morador_nao_pode_atualizar_tarefa(servico, consulta, id_tarefa, registro_tarefa):
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


def test_morador_nao_pode_excluir_tarefa(servico, consulta, id_tarefa, registro_tarefa):
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
        SimpleNamespace(data=[{"fk_usuario_id": registro_tarefa["fk_usuario_id"]}]),
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
    consulta.update.assert_called_once_with({"dificuldade": 3, "pontuacao": 50})


def test_atualizar_tarefa_rejeita_responsaveis_duplicados():
    usuario = uuid4()
    with pytest.raises(ValidationError):
        TarefaAtualizar(usuarios_atribuidos=[usuario, usuario])


def test_atualizar_tarefa_rejeita_responsavel_de_outra_casa(
    servico, consulta, id_tarefa, registro_tarefa
):
    usuario_estranho = uuid4()

    # 1. Busca tarefa, 2. autoriza pela casa, 3. busca a casa (dono) e
    # 4. busca os vínculos 'pertencer' da casa para validar os responsáveis.
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": registro_tarefa["fk_usuario_id"]}]),
        SimpleNamespace(data=[{"fk_usuario_id": registro_tarefa["fk_usuario_id"]}]),
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
        SimpleNamespace(data=[{"fk_usuario_id": dono_id, "fk_tarefa_id": registro_tarefa["id"]}]),
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": dono_id}]),
    ]

    resultado = servico.atualizar_tarefa(
        id_tarefa,
        TarefaAtualizar(usuarios_atribuidos=[UUID(dono_id)]),
        UUID(dono_id),
    )

    assert resultado["usuarios_atribuidos"] == [dono_id]


def test_buscar_tarefa_expirada_vira_nao_feito(servico, consulta, registro_tarefa):
    expirada = {
        **registro_tarefa,
        "estado_atual": "atrasada",
        "atraso_maximo": 5,
        "data_fim": "2020-01-01T00:00:00Z",
    }
    marcada_como_nao_feito = {**expirada, "estado_atual": "nao_feito"}

    # 1. Busca tarefa, 2. sincroniza o estado (atraso > atraso_maximo) e
    # 3. busca os usuários atribuídos.
    consulta.execute.side_effect = [
        SimpleNamespace(data=[expirada]),
        SimpleNamespace(data=[marcada_como_nao_feito]),
        SimpleNamespace(data=[]),
    ]

    resultado = servico.buscar_tarefa(UUID(expirada["id"]))

    assert resultado["estado_atual"] == "nao_feito"
    consulta.update.assert_called_once_with({"estado_atual": "nao_feito"})


def test_buscar_tarefa_dentro_do_atraso_maximo_nao_muda_estado(servico, consulta, registro_tarefa):
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


def test_buscar_tarefa_finalizada_nao_e_resincronizada(servico, consulta, registro_tarefa):
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


@pytest.mark.parametrize("campo,valor", [("peso", 3), ("prazo_dias", 5), ("atraso_maximo", 2)])
def test_morador_nao_pode_alterar_regras_de_pontuacao(
    servico, consulta, registro_tarefa, campo, valor
):
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_tarefa]),
        SimpleNamespace(data=[{"fk_usuario_id": registro_tarefa["fk_usuario_id"]}]),
    ]
    with pytest.raises(HTTPException) as erro:
        servico.atualizar_tarefa(
            UUID(registro_tarefa["id"]), TarefaAtualizar(**{campo: valor}), uuid4()
        )
    assert erro.value.status_code == 403
    consulta.update.assert_not_called()


@pytest.mark.parametrize(
    "atraso,expirada",
    [
        (timedelta(days=1), False),
        (timedelta(days=2), False),
        (timedelta(days=2, microseconds=1), True),
        (timedelta(days=3), True),
    ],
)
def test_tolerancia_preserva_pontos_ate_ultimo_dia(
    servico, consulta, registro_tarefa, monkeypatch, atraso, expirada
):
    agora = datetime(2030, 1, 10, tzinfo=timezone.utc)

    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):
            return agora

    monkeypatch.setattr("services.tarefa.datetime", Relogio)
    tarefa = {**registro_tarefa, "data_fim": (agora - atraso).isoformat(), "atraso_maximo": 2}
    consulta.execute.return_value = SimpleNamespace(data=[{**tarefa, "estado_atual": "nao_feito"}])
    resultado = servico._sincronizar_estado_por_atraso(tarefa)
    assert (resultado["estado_atual"] == "nao_feito") is expirada
    assert consulta.update.called is expirada


def test_editar_prazo_preserva_inicio_original(servico, consulta, registro_tarefa):
    inicio = datetime.now(timezone.utc) - timedelta(days=1)
    tarefa = {**registro_tarefa, "data_inicio": inicio.isoformat(), "prazo_dias": 3}
    servico._buscar_tarefa_bruta = MagicMock(return_value=tarefa)
    servico.buscar_tarefa = MagicMock(return_value=tarefa)
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"fk_usuario_id": tarefa["fk_usuario_id"]}]),
        SimpleNamespace(data=[tarefa]),
    ]
    servico.atualizar_tarefa(
        UUID(tarefa["id"]), TarefaAtualizar(prazo_dias=5), UUID(tarefa["fk_usuario_id"])
    )
    consulta.update.assert_called_once_with(
        {
            "prazo_dias": 5,
            "data_fim": (inicio + timedelta(days=5)).isoformat(),
        }
    )


@pytest.mark.parametrize("alteracao", [{"prazo_dias": 5}, {"atraso_maximo": 4}])
def test_edicao_nao_pode_invadir_proxima_ocorrencia(servico, consulta, registro_tarefa, alteracao):
    inicio = datetime.now(timezone.utc) + timedelta(days=1)
    tarefa = {
        **registro_tarefa,
        "referencia_inicio": "ocorrencia",
        "data_inicio": inicio.isoformat(),
        "prazo_dias": 3,
        "atraso_maximo": 2,
        "data_fim": (inicio + timedelta(days=3)).isoformat(),
        "proxima_ocorrencia": (inicio + timedelta(days=7)).isoformat(),
    }
    servico._buscar_tarefa_bruta = MagicMock(return_value=tarefa)
    consulta.execute.return_value = SimpleNamespace(
        data=[{"fk_usuario_id": tarefa["fk_usuario_id"]}]
    )
    with pytest.raises(HTTPException) as erro:
        servico.atualizar_tarefa(
            UUID(tarefa["id"]), TarefaAtualizar(**alteracao), UUID(tarefa["fk_usuario_id"])
        )
    assert erro.value.status_code == 422
    consulta.update.assert_not_called()


def test_ocorrencia_nao_pode_ser_concluida_antes_do_inicio(servico, consulta, registro_tarefa):
    tarefa = {
        **registro_tarefa,
        "data_inicio": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    }
    servico._buscar_tarefa_bruta = MagicMock(return_value=tarefa)
    consulta.execute.return_value = SimpleNamespace(
        data=[{"fk_usuario_id": tarefa["fk_usuario_id"]}]
    )
    with pytest.raises(HTTPException) as erro:
        servico.atualizar_tarefa(
            UUID(tarefa["id"]),
            TarefaAtualizar(estado_atual="finalizado"),
            UUID(tarefa["fk_usuario_id"]),
        )
    assert erro.value.status_code == 409
    consulta.update.assert_not_called()


def test_finalizacao_nao_pode_alterar_peso_ao_mesmo_tempo(servico, consulta, registro_tarefa):
    servico._buscar_tarefa_bruta = MagicMock(return_value=registro_tarefa)
    with pytest.raises(HTTPException) as erro:
        servico.atualizar_tarefa(
            UUID(registro_tarefa["id"]),
            TarefaAtualizar(estado_atual="finalizado", peso=3),
            UUID(registro_tarefa["fk_usuario_id"]),
        )
    assert erro.value.status_code == 422
    consulta.update.assert_not_called()


@pytest.mark.parametrize("estado", ["finalizado", "nao_feito"])
def test_administrador_nao_reabre_tarefa_encerrada(servico, consulta, registro_tarefa, estado):
    tarefa = {**registro_tarefa, "estado_atual": estado}
    servico._buscar_tarefa_bruta = MagicMock(return_value=tarefa)
    consulta.execute.return_value = SimpleNamespace(
        data=[{"fk_usuario_id": tarefa["fk_usuario_id"]}]
    )
    with pytest.raises(HTTPException) as erro:
        servico.atualizar_tarefa(
            UUID(tarefa["id"]),
            TarefaAtualizar(estado_atual="pendente"),
            UUID(tarefa["fk_usuario_id"]),
        )
    assert erro.value.status_code == 409
    consulta.update.assert_not_called()


def test_responsavel_invalido_nao_produz_edicao_parcial(servico, consulta, registro_tarefa):
    servico._buscar_tarefa_bruta = MagicMock(return_value=registro_tarefa)
    dono = registro_tarefa["fk_usuario_id"]
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"fk_usuario_id": dono}]),
        SimpleNamespace(data=[{"fk_usuario_id": dono}]),
        SimpleNamespace(data=[]),
    ]
    with pytest.raises(HTTPException) as erro:
        servico.atualizar_tarefa(
            UUID(registro_tarefa["id"]),
            TarefaAtualizar(peso=3, usuarios_atribuidos=[uuid4()]),
            UUID(dono),
        )
    assert erro.value.status_code == 400
    consulta.update.assert_not_called()
    consulta.delete.assert_not_called()


@pytest.mark.parametrize("codigo,esperado", [("PT409", 409), ("08006", None)])
def test_erro_na_persistencia_nao_produz_gravacoes_separadas(
    servico, banco, consulta, registro_tarefa, codigo, esperado
):
    banco.rpc.return_value.execute.side_effect = APIError(
        {
            "code": codigo,
            "message": "Falha simulada",
            "details": None,
            "hint": None,
        }
    )
    with pytest.raises(HTTPException if esperado else APIError) as erro:
        servico._finalizar_tarefa(registro_tarefa, [registro_tarefa["fk_usuario_id"]])
    if esperado:
        assert erro.value.status_code == esperado
    consulta.insert.assert_not_called()
    consulta.update.assert_not_called()


def test_tolerancia_ultrapassada_durante_conclusao_nao_credita(servico, banco, registro_tarefa):
    tarefa = {
        **registro_tarefa,
        "atraso_maximo": 2,
        "data_fim": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
    }
    with pytest.raises(HTTPException) as erro:
        servico._finalizar_tarefa(tarefa, [tarefa["fk_usuario_id"]])
    assert erro.value.status_code == 409
    banco.rpc.assert_not_called()


@pytest.mark.parametrize("responsaveis", [[], [str(uuid4()), str(uuid4())]])
def test_conclusao_legada_exige_um_responsavel(servico, banco, registro_tarefa, responsaveis):
    with pytest.raises(HTTPException) as erro:
        servico._finalizar_tarefa(registro_tarefa, responsaveis)
    assert erro.value.status_code == 409
    banco.rpc.assert_not_called()


def test_responsavel_nao_finaliza_duas_vezes(servico, banco, consulta, registro_tarefa):
    finalizada = {**registro_tarefa, "estado_atual": "finalizado"}
    consulta.execute.side_effect = [
        SimpleNamespace(data=[finalizada]),
        SimpleNamespace(data=[{"fk_usuario_id": finalizada["fk_usuario_id"]}]),
    ]
    with pytest.raises(HTTPException) as erro:
        servico.atualizar_tarefa(
            UUID(finalizada["id"]),
            TarefaAtualizar(estado_atual="finalizado"),
            UUID(finalizada["fk_usuario_id"]),
        )
    assert erro.value.status_code == 409
    banco.rpc.assert_not_called()


def test_consulta_expirada_nao_sobrescreve_conclusao_concorrente(
    servico, consulta, registro_tarefa
):
    tarefa = {**registro_tarefa, "data_fim": "2020-01-01T00:00:00Z"}
    finalizada = {**tarefa, "estado_atual": "finalizado"}
    consulta.execute.side_effect = [SimpleNamespace(data=[]), SimpleNamespace(data=[finalizada])]
    resultado = servico._sincronizar_estado_por_atraso(tarefa)
    assert resultado["estado_atual"] == "finalizado"
    consulta.in_.assert_called_once_with("estado_atual", ["pendente", "atrasada"])


def test_resposta_explicita_utc_para_datas_legadas_sem_fuso(
    servico, consulta, registro_tarefa
):
    tarefa = {
        **registro_tarefa,
        "estado_atual": "finalizado",
        "data_inicio": "2026-09-01T08:00:00",
        "data_fim": "2026-09-02T08:00:00",
        "concluida_em": "2026-09-02T07:00:00",
    }
    consulta.execute.return_value = SimpleNamespace(data=[])

    resposta = servico._montar_resposta(tarefa)

    assert resposta["data_inicio"] == "2026-09-01T08:00:00+00:00"
    assert resposta["data_fim"] == "2026-09-02T08:00:00+00:00"
    assert resposta["concluida_em"] == "2026-09-02T07:00:00+00:00"

def test_reabrir_tarefa_usa_rpc_atomica(servico, banco, consulta, registro_tarefa):
    tarefa_reaberta = {**registro_tarefa, "estado_atual": "pendente", "concluida_em": None}
    chamada = MagicMock()
    chamada.execute.return_value = SimpleNamespace(data=tarefa_reaberta)
    banco.rpc.return_value = chamada
    servico._montar_resposta = MagicMock(return_value={"id": tarefa_reaberta["id"]})

    assert servico._reabrir_tarefa(registro_tarefa) == {"id": tarefa_reaberta["id"]}
    banco.rpc.assert_called_once_with(
        "reabrir_tarefa_com_reversao", {"p_id_tarefa": registro_tarefa["id"]}
    )
    consulta.insert.assert_not_called()
    consulta.update.assert_not_called()


def test_reabrir_tarefa_sem_resultado_da_500(servico, banco, registro_tarefa):
    chamada = MagicMock()
    chamada.execute.return_value = SimpleNamespace(data=None)
    banco.rpc.return_value = chamada

    with pytest.raises(HTTPException) as erro:
        servico._reabrir_tarefa(registro_tarefa)

    assert erro.value.status_code == 500
