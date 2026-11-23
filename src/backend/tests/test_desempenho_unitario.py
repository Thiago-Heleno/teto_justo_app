from copy import deepcopy
from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest

from test_servico_placar_unitario import evento, montar_servico


@pytest.mark.parametrize(
    "periodo,agora,inicio,fim",
    [
        ("semanal", "2027-01-02T12:00:00Z", "2026-12-27", "2027-01-03"),
        ("semanal", "2027-01-03T03:00:00Z", "2027-01-03", "2027-01-04"),
        ("mensal", "2028-02-29T12:00:00Z", "2028-02-01", "2028-03-01"),
        ("semestral", "2028-06-30T12:00:00Z", "2028-01-01", "2028-07-01"),
        ("semestral", "2028-07-01T03:00:00Z", "2028-07-01", "2028-07-02"),
        ("semestral", "2027-01-01T02:59:59Z", "2026-07-01", "2027-01-01"),
    ],
)
def test_janelas_geram_dias_continuos_ate_hoje_no_fuso_da_casa(periodo, agora, inicio, fim):
    servico, _, casa_id, _ = montar_servico()

    resposta = servico.obter_desempenho(casa_id, periodo, datetime.fromisoformat(agora))

    assert resposta["periodo"] == periodo
    assert resposta["fuso_horario"] == "America/Sao_Paulo"
    assert resposta["data_inicio"] == date.fromisoformat(inicio)
    assert resposta["data_fim"] == date.fromisoformat(fim)
    quantidade = (date.fromisoformat(fim) - date.fromisoformat(inicio)).days
    assert resposta["moradores"][0]["serie"] == [
        {"data": date.fromisoformat(inicio) + timedelta(days=i), "pontos": 0, "acumulado": 0}
        for i in range(quantidade)
    ]


def test_desempenho_soma_creditos_e_estornos_no_dia_local_sem_trazer_saldo_anterior():
    servico, banco, casa_id, usuario_id = montar_servico(score=999)
    banco.registros["score_event"] = [
        evento(casa_id, usuario_id, "2026-11-01T02:59:59Z", 100),
        evento(casa_id, usuario_id, "2026-11-01T03:00:00Z", 25),
        evento(casa_id, usuario_id, "2026-11-02T02:59:59Z", 10),
        evento(casa_id, usuario_id, "2026-11-02T03:00:00Z", -50),
        evento(casa_id, usuario_id, "2026-11-03T12:00:00Z", 5),
        evento(casa_id, usuario_id, "2026-11-03T12:00:00.000001Z", 999),
        evento(casa_id, usuario_id, "2026-11-04T03:00:00Z", 999),
    ]

    resposta = servico.obter_desempenho(
        casa_id, "mensal", datetime.fromisoformat("2026-11-03T12:00:00Z")
    )

    assert resposta["moradores"] == [
        {
            "usuario_id": str(usuario_id),
            "nome": "Ana",
            "total": -10,
            "serie": [
                {"data": date(2026, 11, 1), "pontos": 35, "acumulado": 35},
                {"data": date(2026, 11, 2), "pontos": -50, "acumulado": -15},
                {"data": date(2026, 11, 3), "pontos": 5, "acumulado": -10},
            ],
        }
    ]


def test_desempenho_compara_moradores_ativos_incluindo_zeros_e_pagina_todo_o_historico():
    servico, banco, casa_id, usuario_id = montar_servico()
    servico.TAMANHO_PAGINA = 2
    for nome, ativo in [("Bia", True), ("Caio", True), ("Antigo", False)]:
        outro_id = str(uuid4())
        banco.registros["usuario"].append({"id": outro_id, "nome": nome})
        banco.registros["pertencer"].append(
            {
                "fk_casa_id": str(casa_id),
                "fk_usuario_id": outro_id,
                "score": 0,
                "ativo": ativo,
            }
        )
        if nome != "Caio":
            banco.registros["score_event"].append(
                evento(casa_id, outro_id, "2026-11-01T12:00:00Z", 10)
            )
    banco.registros["score_event"] += [
        evento(casa_id, usuario_id, "2026-11-01T12:00:00Z", 5) for _ in range(5)
    ] + [
        evento(uuid4(), usuario_id, "2026-11-01T12:00:00Z", 999),
        evento(casa_id, uuid4(), "2026-11-01T12:00:00Z", 999),
    ]

    resposta = servico.obter_desempenho(
        casa_id, "semanal", datetime.fromisoformat("2026-11-03T12:00:00Z")
    )

    assert [(m["nome"], m["total"]) for m in resposta["moradores"]] == [
        ("Ana", 25),
        ("Bia", 10),
        ("Caio", 0),
    ]
    assert resposta["moradores"][0]["serie"][1:] == [
        {"data": date(2026, 11, 2), "pontos": 0, "acumulado": 25},
        {"data": date(2026, 11, 3), "pontos": 0, "acumulado": 25},
    ]


def test_nova_consulta_reflete_movimentacoes_sem_cache_e_sem_modificar_os_dados():
    servico, banco, casa_id, usuario_id = montar_servico()
    agora = datetime.fromisoformat("2026-11-03T12:00:00Z")
    assert servico.obter_desempenho(casa_id, "semanal", agora)["moradores"][0]["total"] == 0
    for pontos, esperado in [(25, 25), (-25, 0), (17, 17)]:
        banco.registros["score_event"].append(
            evento(casa_id, usuario_id, "2026-11-03T12:00:00Z", pontos)
        )
        antes = deepcopy(banco.registros)

        resposta = servico.obter_desempenho(casa_id, "semanal", agora)

        assert resposta["moradores"][0]["total"] == esperado
        assert resposta["atualizado_em"] == agora
        assert banco.registros == antes


@pytest.mark.parametrize("fuso", [None, "America/Invalido"])
def test_desempenho_usa_utc_quando_a_casa_nao_tem_fuso_valido(fuso):
    servico, _, casa_id, _ = montar_servico(fuso=fuso)

    resposta = servico.obter_desempenho(
        casa_id, "mensal", datetime.fromisoformat("2027-01-01T01:00:00Z")
    )

    assert resposta["fuso_horario"] == "UTC"
    assert resposta["data_inicio"] == date(2027, 1, 1)


def test_desempenho_considera_a_mudanca_do_horario_de_verao():
    servico, banco, casa_id, usuario_id = montar_servico(fuso="America/New_York")
    banco.registros["score_event"] = [
        evento(casa_id, usuario_id, "2026-03-08T04:59:59Z", 100),
        evento(casa_id, usuario_id, "2026-03-08T05:00:00Z", 3),
        evento(casa_id, usuario_id, "2026-03-09T03:59:59Z", 5),
        evento(casa_id, usuario_id, "2026-03-09T04:00:00Z", 7),
    ]

    resposta = servico.obter_desempenho(
        casa_id, "semanal", datetime.fromisoformat("2026-03-09T12:00:00Z")
    )

    assert resposta["moradores"][0]["serie"] == [
        {"data": date(2026, 3, 8), "pontos": 8, "acumulado": 8},
        {"data": date(2026, 3, 9), "pontos": 7, "acumulado": 15},
    ]


def test_desempenho_de_casa_sem_moradores_retorna_lista_vazia():
    servico, banco, casa_id, _ = montar_servico()
    banco.registros["pertencer"] = []

    assert servico.obter_desempenho(casa_id)["moradores"] == []
