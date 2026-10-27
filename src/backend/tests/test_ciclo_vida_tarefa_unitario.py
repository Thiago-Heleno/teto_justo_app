from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi import BackgroundTasks, HTTPException
from postgrest.exceptions import APIError

from services.ciclo_vida_tarefa import estado_no_prazo, instante_utc, janela_dia_fixo
from services.penalidade import ServicoPenalidade
from services.tarefa import ServicoTarefa
from test_contrato_casa_router_unitario import ConsultaEmMemoria, SupabaseEmMemoria


@pytest.fixture
def cenario(monkeypatch):
    agora = datetime(2030, 1, 10, 12, tzinfo=timezone.utc)

    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):
            return agora

    monkeypatch.setattr("services.tarefa.datetime", Relogio)
    tarefa = {
        "id": str(uuid4()), "nome": "Limpar cozinha", "estado_atual": "pendente",
        "dificuldade": 2, "pontuacao": 25, "atraso_maximo": 2,
        "data_fim": (agora + timedelta(days=2)).isoformat(),
        "data_inicio": (agora - timedelta(days=1)).isoformat(),
        "fk_casa_id": str(uuid4()), "fk_usuario_id": str(uuid4()), "reaberturas": 0,
    }
    banco = SupabaseEmMemoria({
        "tarefa": [tarefa],
        "atribuida": [{"fk_tarefa_id": tarefa["id"], "fk_usuario_id": tarefa["fk_usuario_id"]}],
        "pertencer": [{
            "fk_casa_id": tarefa["fk_casa_id"], "fk_usuario_id": tarefa["fk_usuario_id"],
            "ativo": True, "score": 100,
        }],
        "score_event": [],
    })
    executar = ConsultaEmMemoria.execute

    def executar_com_unicidade(consulta):
        if consulta.tabela == "score_event" and consulta.acao == "insert":
            if any(
                all(evento[campo] == consulta.dados[campo]
                    for campo in ("fk_usuario_id", "fk_tarefa_id", "tipo", "ciclo"))
                for evento in banco.registros["score_event"]
            ):
                raise APIError({"code": "23505", "message": "Evento já registrado."})
        return executar(consulta)

    monkeypatch.setattr(ConsultaEmMemoria, "execute", executar_com_unicidade)
    return banco, ServicoTarefa(banco, BackgroundTasks()), tarefa, agora


@pytest.mark.parametrize("atraso,esperado", [
    (timedelta(microseconds=-1), "pendente"),
    (timedelta(0), "pendente"),
    (timedelta(microseconds=1), "atrasada"),
    (timedelta(days=2), "atrasada"),
    (timedelta(days=2, microseconds=1), "nao_feito"),
])
def test_estado_respeita_instante_do_prazo_e_limite_da_tolerancia(atraso, esperado):
    prazo = datetime(2030, 1, 10, tzinfo=timezone.utc)
    assert estado_no_prazo({"data_fim": prazo, "atraso_maximo": 2}, prazo + atraso) == esperado


@pytest.mark.parametrize("valor", [
    "2030-01-10T12:00:00", "2030-01-10T12:00:00Z", "2030-01-10T09:00:00-03:00",
    datetime(2030, 1, 10, 12), datetime(2030, 1, 10, 12, tzinfo=timezone.utc),
])
def test_datas_legadas_e_com_fuso_representam_o_mesmo_instante(valor):
    assert instante_utc(valor) == datetime(2030, 1, 10, 12, tzinfo=timezone.utc)


@pytest.mark.parametrize("nome_fuso", ["America/Sao_Paulo", "Asia/Tokyo", "America/New_York"])
def test_dia_fixo_termina_no_ultimo_instante_do_dia_da_casa(nome_fuso):
    fuso = ZoneInfo(nome_fuso)
    dia = date(2026, 11, 1)
    inicio, fim = janela_dia_fixo(dia, 2, fuso)
    assert fim.astimezone(fuso) == datetime.combine(dia, time.max, tzinfo=fuso)
    assert fim - inicio == timedelta(days=2)


@pytest.mark.parametrize("origem", ["leitura", "job"])
@pytest.mark.parametrize("dias_atraso,esperado", [(1, "atrasada"), (3, "nao_feito")])
def test_leitura_e_job_aplicam_a_mesma_transicao_sem_mudar_pontos(
    cenario, origem, dias_atraso, esperado,
):
    banco, servico, tarefa, agora = cenario
    tarefa["data_fim"] = (agora - timedelta(days=dias_atraso)).isoformat()
    if origem == "leitura":
        assert servico.buscar_tarefa(UUID(tarefa["id"]))["estado_atual"] == esperado
    else:
        ServicoPenalidade(banco, BackgroundTasks()).processar_tarefas(agora)
    assert tarefa["estado_atual"] == esperado
    assert banco.registros["score_event"] == []
    assert banco.registros["pertencer"][0]["score"] == 100


def test_conclusao_repetida_nao_duplica_credito(cenario):
    banco, servico, tarefa, _ = cenario
    resultado = servico.concluir_tarefa(UUID(tarefa["id"]), UUID(tarefa["fk_usuario_id"]))
    assert resultado["resultado_pontuacao"]["saldo_atual"] == 125
    with pytest.raises(HTTPException) as erro:
        servico.concluir_tarefa(UUID(tarefa["id"]), UUID(tarefa["fk_usuario_id"]))
    assert erro.value.status_code == 409
    assert banco.registros["pertencer"][0]["score"] == 125
    assert len(banco.registros["score_event"]) == 1


@pytest.mark.parametrize("dias_atraso,esperado", [
    (-1, "pendente"), (1, "atrasada"), (3, "nao_feito"),
])
def test_reaberturas_do_mesmo_ciclo_estornam_uma_unica_vez(cenario, dias_atraso, esperado):
    banco, servico, tarefa, agora = cenario
    servico.concluir_tarefa(UUID(tarefa["id"]), UUID(tarefa["fk_usuario_id"]))
    tarefa["data_fim"] = (agora - timedelta(days=dias_atraso)).isoformat()
    finalizada = deepcopy(tarefa)
    primeira = servico.ciclo_vida.reabrir(finalizada, [tarefa["fk_usuario_id"]], agora)
    segunda = servico.ciclo_vida.reabrir(finalizada, [tarefa["fk_usuario_id"]], agora)
    assert primeira == segunda
    assert primeira["estado_atual"] == esperado
    assert primeira["reaberturas"] == 1
    assert banco.registros["pertencer"][0]["score"] == 100
    assert [evento["pontuacao"] for evento in banco.registros["score_event"]] == [25, -25]


def test_nova_conclusao_apos_reabertura_credita_o_novo_ciclo(cenario):
    banco, servico, tarefa, _ = cenario
    id_tarefa, id_usuario = UUID(tarefa["id"]), UUID(tarefa["fk_usuario_id"])
    servico.concluir_tarefa(id_tarefa, id_usuario)
    servico.reabrir_tarefa(id_tarefa, id_usuario)
    resultado = servico.concluir_tarefa(id_tarefa, id_usuario)
    assert resultado["resultado_pontuacao"]["saldo_atual"] == 125
    assert [(e["tipo"], e["ciclo"]) for e in banco.registros["score_event"]] == [
        ("credito", 0), ("reversal", 0), ("credito", 1),
    ]


def test_conclusao_de_ciclo_antigo_nao_finaliza_ciclo_novo(cenario):
    banco, servico, tarefa, agora = cenario
    original = deepcopy(tarefa)
    id_tarefa, id_usuario = UUID(tarefa["id"]), UUID(tarefa["fk_usuario_id"])
    servico.concluir_tarefa(id_tarefa, id_usuario)
    servico.reabrir_tarefa(id_tarefa, id_usuario)

    with pytest.raises(HTTPException) as erro:
        servico.ciclo_vida.concluir(original, [str(id_usuario)], agora)

    assert erro.value.status_code == 409
    assert tarefa["estado_atual"] == "pendente"
    assert tarefa["reaberturas"] == 1
    assert banco.registros["pertencer"][0]["score"] == 100
    assert len(banco.registros["score_event"]) == 2


def test_conflito_no_saldo_refaz_o_cas_sem_perder_credito_concorrente(cenario, monkeypatch):
    banco, servico, tarefa, _ = cenario
    executar = ConsultaEmMemoria.execute
    conflito = False

    def executar_com_conflito(consulta):
        nonlocal conflito
        if consulta.tabela == "pertencer" and consulta.acao == "update" and not conflito:
            conflito = True
            banco.registros["pertencer"][0]["score"] += 7
        return executar(consulta)

    monkeypatch.setattr(ConsultaEmMemoria, "execute", executar_com_conflito)
    resultado = servico.concluir_tarefa(UUID(tarefa["id"]), UUID(tarefa["fk_usuario_id"]))
    assert conflito
    assert resultado["resultado_pontuacao"]["saldo_atual"] == 132
    assert len(banco.registros["score_event"]) == 1


def test_erro_no_evento_nao_muda_saldo_nem_finaliza(cenario, monkeypatch):
    banco, servico, tarefa, _ = cenario
    executar = ConsultaEmMemoria.execute

    def executar_com_falha(consulta):
        if consulta.tabela == "score_event" and consulta.acao == "insert":
            raise APIError({"code": "08006", "message": "Falha de conexão simulada."})
        return executar(consulta)

    monkeypatch.setattr(ConsultaEmMemoria, "execute", executar_com_falha)
    with pytest.raises(APIError):
        servico.concluir_tarefa(UUID(tarefa["id"]), UUID(tarefa["fk_usuario_id"]))
    assert tarefa["estado_atual"] == "pendente"
    assert banco.registros["pertencer"][0]["score"] == 100
    assert banco.registros["score_event"] == []
