from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError
from postgrest.exceptions import APIError

from schemas.rotatividade import RotatividadeCriar
from schemas.tarefa import TarefaAtualizar, TarefaCriar
from services.autorizacao import ServicoAutorizacaoCasa
from services.rotatividade import (
    ServicoRotatividade,
    _mes_local,
    escolher_responsavel,
    gerar_janelas,
    semana_ancora,
)
from services.tarefa import ServicoTarefa


def _config(**alteracoes):
    config = {
        "id": str(uuid4()),
        "fk_casa_id": str(uuid4()),
        "criado_em": "2026-09-01T12:00:00Z",
        "semana_ancora": "2026-08-31",
        "dias_semana": [1, 3],
        "intervalo_semanas": 2,
        "modo_prazo": "intervalo",
        "prazo_dias": 2,
    }
    config.update(alteracoes)
    return config


def test_escolha_equilibra_potencial_mensal_e_desempata_pela_ordem():
    participantes = [
        {"fk_usuario_id": "primeiro", "ordem": 1},
        {"fk_usuario_id": "segundo", "ordem": 2},
        {"fk_usuario_id": "terceiro", "ordem": 3},
    ]
    assert escolher_responsavel(
        participantes, {"primeiro": 50, "segundo": 25, "terceiro": 25}
    ) == "segundo"
    assert escolher_responsavel(
        participantes, {"primeiro": 0, "segundo": 25, "terceiro": 25}
    ) == "primeiro"
    # A escolha anterior não cria uma restrição artificial contra repetições.
    assert escolher_responsavel(participantes, {"primeiro": 0}) == "primeiro"


def test_primeira_semana_nao_pula_proximo_dia_de_intervalo_bissemanal():
    fuso = ZoneInfo("America/Sao_Paulo")
    domingo = datetime(2026, 9, 27, 12, tzinfo=fuso).astimezone(timezone.utc)

    assert semana_ancora([1], "intervalo", 2, fuso, domingo) == date(2026, 9, 28)
    assert semana_ancora([7], "dia_fixo", 2, fuso, domingo) == date(2026, 9, 21)


def test_agenda_repeats_a_cada_duas_semanas_e_recupera_slots_perdidos():
    fuso = ZoneInfo("America/Sao_Paulo")
    agora = datetime(2026, 9, 16, 12, tzinfo=fuso).astimezone(timezone.utc)
    janelas = list(gerar_janelas(_config(), fuso, agora))
    datas = [slot.astimezone(fuso).date() for slot, _, _ in janelas]
    assert datas == [date(2026, 9, 2), date(2026, 9, 14), date(2026, 9, 16)]
    assert all(fim - inicio == timedelta(days=2) for _, inicio, fim in janelas)


def test_dia_fixo_abre_antes_do_vencimento_e_pode_sobrepor_ocorrencias():
    fuso = ZoneInfo("America/Sao_Paulo")
    config = _config(
        criado_em="2026-09-01T00:00:00Z",
        dias_semana=[1, 3],
        intervalo_semanas=1,
        modo_prazo="dia_fixo",
        prazo_dias=5,
    )
    agora = datetime(2026, 9, 11, 12, tzinfo=fuso).astimezone(timezone.utc)
    janelas = list(gerar_janelas(config, fuso, agora))
    futuros = [(slot, inicio, fim) for slot, inicio, fim in janelas if slot > agora]
    assert [slot.astimezone(fuso).date() for slot, _, _ in futuros] == [date(2026, 9, 14)]
    assert futuros[0][1] <= agora < futuros[0][2]
    assert len([slot for slot, _, _ in janelas if slot.astimezone(fuso).month == 9]) >= 3


def test_mes_local_respeita_fronteira_no_fuso_da_casa():
    fuso = ZoneInfo("America/Sao_Paulo")
    slot = datetime(2026, 10, 1, 2, tzinfo=timezone.utc)
    inicio, fim = _mes_local(slot, fuso)
    assert inicio == datetime(2026, 9, 1, 3, tzinfo=timezone.utc)
    assert fim == datetime(2026, 10, 1, 3, tzinfo=timezone.utc)


def test_janela_dia_fixo_usa_fim_do_dia_local():
    fuso = ZoneInfo("America/Sao_Paulo")
    inicio, fim = ServicoTarefa.janela_dia_fixo(date(2026, 10, 8), 3, fuso)
    assert fim.astimezone(fuso).date() == date(2026, 10, 8)
    assert fim.astimezone(fuso).time().isoformat() == "23:59:59.999999"
    assert fim - inicio == timedelta(days=3)


def test_criacao_unitaria_dia_fixo_persiste_janela_e_tipo():
    banco = MagicMock()
    consulta = banco.table.return_value
    for metodo in ["select", "eq", "in_", "insert"]:
        getattr(consulta, metodo).return_value = consulta
    usuario = uuid4()
    casa = uuid4()
    tarefa_id = uuid4()
    inicio, fim = ServicoTarefa.janela_dia_fixo(
        date(2030, 1, 15), 3, ZoneInfo("America/Sao_Paulo")
    )
    registro = {
        "id": str(tarefa_id), "nome": "Limpar cozinha", "descricao": None,
        "estado_atual": "pendente", "dificuldade": 2, "pontuacao": 25,
        "atraso_maximo": 2, "prazo_dias": 3, "tipo": "unitaria",
        "modo_prazo": "dia_fixo", "timezone": "America/Sao_Paulo",
        "data_inicio": inicio.isoformat(),
        "data_fim": fim.isoformat(), "fk_casa_id": str(casa),
        "fk_usuario_id": str(usuario),
    }
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"fk_usuario_id": str(usuario)}]),
        SimpleNamespace(data=[{"fk_usuario_id": str(usuario)}]),
        SimpleNamespace(data=[{"timezone": "America/Sao_Paulo"}]),
        SimpleNamespace(data=[registro]),
        SimpleNamespace(data=[{"fk_usuario_id": str(usuario)}]),
        SimpleNamespace(data=[{"fk_usuario_id": str(usuario)}]),
    ]
    resposta = ServicoTarefa(banco).criar_tarefa(TarefaCriar(
        nome="Limpar cozinha", peso=2, prazo_dias=3, atraso_maximo=2,
        modo_prazo="dia_fixo", data_fixa=date(2030, 1, 15),
        fk_casa_id=casa, usuarios_atribuidos=[usuario],
    ), usuario)
    gravada = consulta.insert.call_args_list[0].args[0]
    assert gravada["tipo"] == "unitaria"
    assert gravada["modo_prazo"] == "dia_fixo"
    assert gravada["timezone"] == "America/Sao_Paulo"
    assert gravada["data_inicio"] == inicio.isoformat()
    assert gravada["data_fim"] == fim.isoformat()
    assert resposta["data_fixa"] == "2030-01-15"


def test_edicao_dia_fixo_recalcula_abertura_com_novo_prazo():
    banco = MagicMock()
    consulta = banco.table.return_value
    for metodo in ["select", "eq", "update"]:
        getattr(consulta, metodo).return_value = consulta
    servico = ServicoTarefa(banco)
    usuario = uuid4()
    casa = uuid4()
    tarefa_id = uuid4()
    inicio, fim = ServicoTarefa.janela_dia_fixo(
        date(2030, 1, 15), 2, ZoneInfo("America/Sao_Paulo")
    )
    registro = {
        "id": str(tarefa_id), "fk_casa_id": str(casa),
        "fk_usuario_id": str(usuario), "estado_atual": "pendente",
        "tipo": "unitaria", "modo_prazo": "dia_fixo", "prazo_dias": 2,
        "timezone": "America/Sao_Paulo",
        "data_inicio": inicio.isoformat(), "data_fim": fim.isoformat(),
        "atraso_maximo": 2,
    }
    servico._buscar_tarefa_bruta = MagicMock(return_value=registro)
    servico.buscar_tarefa = MagicMock(return_value=registro)
    servico._fuso_casa = MagicMock(return_value=ZoneInfo("America/Sao_Paulo"))
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"fk_usuario_id": str(usuario)}]),
        SimpleNamespace(data=[registro]),
    ]
    servico.atualizar_tarefa(
        tarefa_id,
        TarefaAtualizar(prazo_dias=4, data_fixa=date(2030, 1, 20)),
        usuario,
    )
    novo_inicio, novo_fim = ServicoTarefa.janela_dia_fixo(
        date(2030, 1, 20), 4, ZoneInfo("America/Sao_Paulo")
    )
    consulta.update.assert_called_once_with({
        "prazo_dias": 4,
        "data_inicio": novo_inicio.isoformat(),
        "data_fim": novo_fim.isoformat(),
    })


def test_data_fixa_preserva_fuso_da_tarefa_apos_mudanca_da_casa():
    servico = ServicoTarefa(MagicMock())
    servico._fuso_casa = MagicMock(side_effect=AssertionError("Não consulte o fuso atual"))
    servico._buscar_usuarios_atribuidos = MagicMock(return_value=[str(uuid4())])
    _, fim = ServicoTarefa.janela_dia_fixo(
        date(2030, 1, 15), 2, ZoneInfo("America/Sao_Paulo")
    )
    tarefa = {
        "id": str(uuid4()), "fk_casa_id": str(uuid4()),
        "fk_usuario_id": str(uuid4()), "nome": "Limpeza", "descricao": None,
        "estado_atual": "pendente", "dificuldade": 1, "prazo_dias": 2,
        "atraso_maximo": 2, "tipo": "unitaria", "modo_prazo": "dia_fixo",
        "timezone": "America/Sao_Paulo", "data_fim": fim.isoformat(),
    }
    assert servico._montar_resposta(tarefa)["data_fixa"] == "2030-01-15"
    servico._fuso_casa.assert_not_called()


def test_schema_rejeita_atraso_e_participantes_invalidos():
    payload = {
        "fk_casa_id": uuid4(),
        "nome": "Lixo",
        "peso": 2,
        "prazo_dias": 2,
        "atraso_maximo": 5,
        "modo_prazo": "intervalo",
        "participantes": [uuid4(), uuid4()],
        "dias_semana": [1, 3],
        "intervalo_semanas": 1,
    }
    assert RotatividadeCriar(**payload).dias_semana == [1, 3]
    for alteracao in [
        {"atraso_maximo": 6},
        {"participantes": [payload["participantes"][0]] * 2},
        {"dias_semana": [1, 1]},
        {"intervalo_semanas": 5},
    ]:
        with pytest.raises(ValidationError):
            RotatividadeCriar(**(payload | alteracao))


def test_potencial_mensal_soma_todas_as_rotatividades_da_casa():
    banco = MagicMock()
    consulta = banco.table.return_value
    for metodo in ["select", "eq", "gte", "lt", "range", "in_", "order"]:
        getattr(consulta, metodo).return_value = consulta
    consulta.not_.is_.return_value = consulta
    tarefas = [
        {"id": "tarefa-1", "pontuacao": 10},
        {"id": "tarefa-2", "pontuacao": 50},
        {"id": "tarefa-3", "pontuacao": 25},
    ]
    atribuicoes = [
        {"fk_tarefa_id": "tarefa-1", "fk_usuario_id": "primeiro"},
        {"fk_tarefa_id": "tarefa-2", "fk_usuario_id": "primeiro"},
        {"fk_tarefa_id": "tarefa-3", "fk_usuario_id": "segundo"},
    ]
    consulta.execute.side_effect = [
        SimpleNamespace(data=tarefas), SimpleNamespace(data=atribuicoes)
    ]
    potenciais = ServicoRotatividade(banco)._potenciais_mes(
        {"id": "casa", "timezone": "America/Sao_Paulo"},
        datetime(2026, 9, 15, tzinfo=timezone.utc),
        [
            {"fk_usuario_id": "primeiro", "ordem": 1},
            {"fk_usuario_id": "segundo", "ordem": 2},
        ],
    )
    assert potenciais == {"primeiro": 60, "segundo": 25}
    assert consulta.gte.call_args.args[1] == "2026-09-01T03:00:00+00:00"
    assert consulta.lt.call_args.args[1] == "2026-10-01T03:00:00+00:00"


def test_concorrencia_reconsulta_potenciais_apos_versao_desatualizada():
    banco = MagicMock()
    servico = ServicoRotatividade(banco)
    id_casa = str(uuid4())
    servico._casa = MagicMock(side_effect=[
        {"id": id_casa, "timezone": "America/Sao_Paulo", "rotacao_versao": 1},
        {"id": id_casa, "timezone": "America/Sao_Paulo", "rotacao_versao": 2},
    ])
    servico._potenciais_mes = MagicMock(side_effect=[
        {"primeiro": 0, "segundo": 0},
        {"primeiro": 25, "segundo": 0},
    ])
    banco.rpc.return_value.execute.side_effect = [
        APIError({"code": "PT409", "message": "Rodízio alterado. Recalcule a distribuição."}),
        SimpleNamespace(data={"id": str(uuid4())}),
    ]
    participantes = [
        {"fk_usuario_id": "primeiro", "ordem": 1},
        {"fk_usuario_id": "segundo", "ordem": 2},
    ]
    instante = datetime(2026, 9, 16, tzinfo=timezone.utc)
    servico._registrar(
        {"id": str(uuid4()), "fk_casa_id": id_casa, "timezone": "America/Sao_Paulo"},
        participantes,
        instante,
        instante,
        instante + timedelta(days=2),
    )
    chamadas = banco.rpc.call_args_list
    assert chamadas[0].args[1]["p_id_usuario"] == "primeiro"
    assert chamadas[1].args[1]["p_id_usuario"] == "segundo"
    assert chamadas[1].args[1]["p_versao_casa"] == 2


def test_criacao_refaz_ancora_se_fuso_da_casa_mudar(monkeypatch):
    monkeypatch.setattr(
        ServicoAutorizacaoCasa, "garantir_administrador_da_casa",
        lambda self, *args: None,
    )
    monkeypatch.setattr(
        ServicoAutorizacaoCasa, "garantir_responsaveis_da_casa",
        lambda self, *args: None,
    )
    banco = MagicMock()
    servico = ServicoRotatividade(banco)
    id_casa = uuid4()
    autor = uuid4()
    outro = uuid4()
    servico._casa = MagicMock(side_effect=[
        {"id": str(id_casa), "timezone": "UTC"},
        {"id": str(id_casa), "timezone": "America/Sao_Paulo"},
    ])
    banco.rpc.return_value.execute.side_effect = [
        APIError({"code": "PT409", "message": "O fuso da casa mudou."}),
        SimpleNamespace(data={
            "id": str(uuid4()), "fk_casa_id": str(id_casa),
            "nome": "Lixo", "descricao": None, "dificuldade": 1,
            "pontuacao": 10, "prazo_dias": 2, "atraso_maximo": 2,
            "modo_prazo": "intervalo", "dias_semana": [1],
            "intervalo_semanas": 1, "semana_ancora": "2026-09-21",
            "ativa": True, "criado_em": "2026-09-26T12:00:00Z",
        }),
    ]
    dados = RotatividadeCriar(
        fk_casa_id=id_casa, nome="Lixo", peso=1, prazo_dias=2,
        atraso_maximo=2, modo_prazo="intervalo", participantes=[autor, outro],
        dias_semana=[1], intervalo_semanas=1,
    )
    servico.criar(dados, autor)
    configs = [chamada.args[1]["p_config"] for chamada in banco.rpc.call_args_list]
    assert [config["timezone_esperado"] for config in configs] == [
        "UTC", "America/Sao_Paulo"
    ]


def test_recuperacao_processa_slots_de_rodizios_diferentes_em_ordem(monkeypatch):
    banco = MagicMock()
    servico = ServicoRotatividade(banco)
    casa = str(uuid4())
    config_tarde = {"id": "rodizio-b", "fk_casa_id": casa, "timezone": "UTC"}
    config_cedo = {"id": "rodizio-a", "fk_casa_id": casa, "timezone": "UTC"}
    participante = [{"fk_usuario_id": "morador", "ordem": 1}]
    moradores = [{"fk_usuario_id": "morador"}]
    servico._listar_paginas = MagicMock(side_effect=[
        [config_tarde, config_cedo],
        participante, moradores, [],
        participante, moradores, [],
        [],
    ])
    instante_cedo = datetime(2026, 9, 1, tzinfo=timezone.utc)
    instante_tarde = instante_cedo + timedelta(days=1)

    def janelas(config, *_):
        slot = instante_tarde if config["id"] == "rodizio-b" else instante_cedo
        return [(slot, slot, slot + timedelta(days=1))]

    monkeypatch.setattr("services.rotatividade.gerar_janelas", janelas)
    monkeypatch.setattr(
        ServicoTarefa, "_sincronizar_estado_por_atraso", lambda self, tarefa: tarefa
    )
    servico._registrar = MagicMock(return_value={"id": "tarefa"})
    assert servico.processar_pendentes(instante_tarde + timedelta(days=2)) == 2
    assert [chamada.args[2] for chamada in servico._registrar.call_args_list] == [
        instante_cedo, instante_tarde
    ]
