from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from services.placar import ServicoPlacar


class Consulta:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
        self.filtros = []
        self.ids = None
        self.intervalo = None

    def select(self, _campos):
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor))
        return self

    def in_(self, campo, valores):
        self.ids = (campo, set(valores))
        return self

    def order(self, _campo):
        return self

    def range(self, inicio, fim):
        self.intervalo = (inicio, fim)
        return self

    def execute(self):
        registros = [
            registro for registro in self.banco.registros[self.tabela]
            if all(str(registro.get(campo)) == str(valor) for campo, valor in self.filtros)
            and (self.ids is None or registro.get(self.ids[0]) in self.ids[1])
        ]
        if self.intervalo:
            inicio, fim = self.intervalo
            registros = registros[inicio: fim + 1]
        return SimpleNamespace(data=registros)


class Banco:
    def __init__(self, casa, vinculos, usuarios, eventos):
        self.registros = {
            "casa": casa,
            "pertencer": vinculos,
            "usuario": usuarios,
            "score_event": eventos,
        }

    def table(self, nome):
        return Consulta(self, nome)


def evento(casa_id, usuario_id, instante, pontos):
    return {
        "id": str(uuid4()),
        "fk_casa_id": str(casa_id),
        "fk_usuario_id": str(usuario_id),
        "criado_em": instante,
        "pontuacao": pontos,
    }


def montar_servico(fuso="America/Sao_Paulo", score=0, eventos=None):
    casa_id, usuario_id = uuid4(), uuid4()
    banco = Banco(
        [{"id": str(casa_id), "timezone": fuso, "fk_usuario_id": str(usuario_id)}],
        [{"fk_casa_id": str(casa_id), "fk_usuario_id": str(usuario_id), "score": score}],
        [{"id": str(usuario_id), "nome": "Ana"}],
        eventos or [],
    )
    return ServicoPlacar(banco), banco, casa_id, usuario_id


def test_placar_respeita_semana_domingo_e_virada_de_ano_no_fuso_da_casa():
    servico, banco, casa_id, usuario_id = montar_servico()
    banco.registros["score_event"] = [
        evento(casa_id, usuario_id, "2027-01-01T02:59:59", 2),
        evento(casa_id, usuario_id, "2027-01-01T03:00:00+00:00", 3),
        evento(casa_id, usuario_id, "2027-01-03T02:59:59Z", 5),
        evento(casa_id, usuario_id, "2027-01-03T03:00:00Z", 7),
    ]

    placar = servico.obter_placar(casa_id, datetime(2027, 1, 3, 4, tzinfo=timezone.utc))

    assert placar == {
        "casa_id": str(casa_id),
        "fuso_horario": "America/Sao_Paulo",
        "moradores": [{
            "usuario_id": str(usuario_id),
            "nome": "Ana",
            "semanal": 7,
            "mensal": 15,
            "anual": 15,
            "acumulado": 17,
        }],
    }


def test_placar_usa_meia_noite_local_na_mudanca_do_horario_de_verao():
    servico, banco, casa_id, usuario_id = montar_servico(fuso="America/New_York")
    banco.registros["score_event"] = [
        evento(casa_id, usuario_id, "2026-03-08T04:59:59Z", 2),
        evento(casa_id, usuario_id, "2026-03-08T05:00:00Z", 3),
    ]

    placar = servico.obter_placar(casa_id, datetime(2026, 3, 8, 12, tzinfo=timezone.utc))

    assert placar["moradores"][0]["semanal"] == 3
    assert placar["moradores"][0]["mensal"] == 5


def test_semana_de_janeiro_inclui_eventos_de_dezembro():
    servico, banco, casa_id, usuario_id = montar_servico()
    banco.registros["score_event"] = [
        evento(casa_id, usuario_id, "2026-12-28T12:00:00Z", 4),
        evento(casa_id, usuario_id, "2027-01-01T12:00:00Z", 6),
    ]

    placar = servico.obter_placar(casa_id, datetime(2027, 1, 1, 13, tzinfo=timezone.utc))

    assert placar["moradores"][0]["semanal"] == 10
    assert placar["moradores"][0]["mensal"] == 6
    assert placar["moradores"][0]["anual"] == 6


def test_placar_inclui_morador_sem_eventos_e_eventos_apos_primeira_pagina():
    servico, banco, casa_id, usuario_id = montar_servico()
    outro_id = uuid4()
    banco.registros["usuario"].append({"id": str(outro_id), "nome": "Bia"})
    banco.registros["pertencer"].append({
        "fk_casa_id": str(casa_id), "fk_usuario_id": str(outro_id), "score": 0,
    })
    banco.registros["score_event"] = [
        evento(casa_id, usuario_id, "2026-09-01T12:00:00Z", 1)
        for _ in range(1001)
    ]

    placar = servico.obter_placar(casa_id, datetime(2026, 9, 2, tzinfo=timezone.utc))

    assert placar["moradores"][0]["acumulado"] == 1001
    assert placar["moradores"][1]["acumulado"] == 0


def test_auditoria_aponta_divergencia_sem_alterar_saldo():
    servico, banco, casa_id, usuario_id = montar_servico(score=50)
    banco.registros["score_event"] = [
        evento(casa_id, usuario_id, "2026-09-01T12:00:00Z", 25)
    ]

    assert servico.auditar_saldos(casa_id) == [{
        "usuario_id": str(usuario_id),
        "saldo_materializado": 50,
        "acumulado_eventos": 25,
        "diferenca": 25,
    }]
    assert banco.registros["pertencer"][0]["score"] == 50


def test_auditoria_aponta_evento_sem_vinculo():
    servico, banco, casa_id, _ = montar_servico()
    usuario_antigo = uuid4()
    banco.registros["score_event"] = [
        evento(casa_id, usuario_antigo, "2026-09-01T12:00:00Z", 10)
    ]

    assert servico.auditar_saldos(casa_id) == [{
        "usuario_id": str(usuario_antigo),
        "saldo_materializado": None,
        "acumulado_eventos": 10,
        "diferenca": None,
    }]


def test_placar_restrito_a_moradores():
    servico, _, casa_id, usuario_id = montar_servico()
    servico.garantir_acesso(casa_id, usuario_id)

    with pytest.raises(HTTPException) as erro:
        servico.garantir_acesso(casa_id, uuid4())

    assert erro.value.status_code == 403
