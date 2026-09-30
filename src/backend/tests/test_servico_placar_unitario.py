from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from schemas.score import FiltroExtratoScore, FiltroPeriodoScore
from services.placar import ServicoPlacar


class Consulta:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
        self.filtros = []
        self.ids = None
        self.intervalo = None
        self.ordens = []
        self.periodo = []
        self.campos = "*"

    def select(self, campos, count=None):
        self.campos = campos
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor))
        return self

    def in_(self, campo, valores):
        self.ids = (campo, set(valores))
        return self

    def order(self, campo, desc=False):
        self.ordens.append((campo, desc))
        return self

    def gte(self, campo, valor):
        self.periodo.append((campo, valor, "gte"))
        return self

    def lt(self, campo, valor):
        self.periodo.append((campo, valor, "lt"))
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
        for campo, valor, operador in self.periodo:
            limite = datetime.fromisoformat(valor)
            registros = [
                registro for registro in registros
                if (
                    self.valor_ordenavel(campo, registro[campo]) >= limite
                    if operador == "gte"
                    else self.valor_ordenavel(campo, registro[campo]) < limite
                )
            ]
        total = len(registros)
        for campo, desc in reversed(self.ordens):
            registros.sort(
                key=lambda registro: self.valor_ordenavel(campo, registro[campo]),
                reverse=desc,
            )
        if self.intervalo:
            inicio, fim = self.intervalo
            registros = registros[inicio: fim + 1]
        if self.campos != "*":
            registros = [
                {campo: registro[campo] for campo in self.campos.split(",")}
                for registro in registros
            ]
        return SimpleNamespace(data=registros, count=total)

    @staticmethod
    def valor_ordenavel(campo, valor):
        if campo == "criado_em":
            instante = datetime.fromisoformat(valor)
            return instante if instante.tzinfo else instante.replace(tzinfo=timezone.utc)
        return valor


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
        "fk_tarefa_id": str(uuid4()),
        "tipo": "credito" if pontos >= 0 else "reversal",
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


def test_saldo_consulta_o_vinculo_exato_sem_recalcular_ou_alterar_pontos():
    servico, banco, casa_id, usuario_id = montar_servico(score=75)
    banco.registros["pertencer"].append({
        "fk_casa_id": str(uuid4()), "fk_usuario_id": str(usuario_id), "score": 999,
    })
    banco.registros["score_event"] = [
        evento(casa_id, usuario_id, "2026-09-01T12:00:00Z", 25),
    ]
    antes = deepcopy(banco.registros)

    assert servico.obter_saldo(casa_id, usuario_id) == {
        "fk_casa_id": str(casa_id), "fk_usuario_id": str(usuario_id), "saldo_atual": 75,
    }
    assert banco.registros == antes


def test_ranking_ordena_pontos_empates_e_moradores_sem_eventos_em_varias_paginas():
    servico, banco, casa_id, usuario_id = montar_servico(score=999)
    servico.TAMANHO_PAGINA = 2
    bia, outra_ana, sem_eventos = UUID(int=2), UUID(int=1), UUID(int=3)
    for id_usuario, nome in [(bia, "Bia"), (outra_ana, "Ana"), (sem_eventos, "Caio")]:
        banco.registros["usuario"].append({"id": str(id_usuario), "nome": nome})
        banco.registros["pertencer"].append({
            "fk_casa_id": str(casa_id), "fk_usuario_id": str(id_usuario), "score": 0,
        })
    banco.registros["score_event"] = [
        evento(casa_id, usuario_id, "2026-09-01T12:00:00Z", 25),
        evento(casa_id, bia, "2026-09-02T12:00:00Z", 50),
        evento(casa_id, outra_ana, "2026-09-03T12:00:00Z", 50),
        evento(casa_id, outra_ana, "2026-09-04T12:00:00Z", -25),
        evento(uuid4(), usuario_id, "2026-09-05T12:00:00Z", 999),
        evento(casa_id, uuid4(), "2026-09-05T12:00:00Z", 999),
    ]
    antes = deepcopy(banco.registros)

    ranking = servico.obter_ranking(casa_id, FiltroPeriodoScore())

    assert [
        (item["usuario_id"], item["pontos"], item["posicao"])
        for item in ranking["moradores"]
    ] == [(str(bia), 50, 1), (str(outra_ana), 25, 2),
          (str(usuario_id), 25, 2), (str(sem_eventos), 0, 4)]
    assert banco.registros == antes


@pytest.mark.parametrize("filtros,pontos", [
    ({"data_inicio": "2026-09-01", "data_fim": "2026-10-01"}, 8),
    ({"data_inicio": "2026-09-01"}, 15),
    ({"data_fim": "2026-10-01"}, 10),
    ({}, 17),
])
def test_ranking_e_extrato_respeitam_limites_do_mes_no_fuso_da_casa(filtros, pontos):
    servico, banco, casa_id, usuario_id = montar_servico()
    banco.registros["score_event"] = [
        evento(casa_id, usuario_id, "2026-09-01T02:59:59Z", 2),
        evento(casa_id, usuario_id, "2026-09-01T03:00:00Z", 3),
        evento(casa_id, usuario_id, "2026-10-01T02:59:59.999999Z", 5),
        evento(casa_id, usuario_id, "2026-10-01T03:00:00Z", 7),
    ]

    ranking = servico.obter_ranking(casa_id, FiltroPeriodoScore(**filtros))
    extrato = servico.obter_extrato(casa_id, FiltroExtratoScore(**filtros))

    assert ranking["moradores"][0]["pontos"] == pontos
    assert sum(item["pontuacao"] for item in extrato["eventos"]) == pontos


def test_periodo_respeita_a_mudanca_de_fuso_entre_inicio_e_fim():
    servico, banco, casa_id, usuario_id = montar_servico(fuso="America/New_York")
    banco.registros["score_event"] = [
        evento(casa_id, usuario_id, "2026-03-08T04:59:59Z", 2),
        evento(casa_id, usuario_id, "2026-03-08T05:00:00Z", 3),
        evento(casa_id, usuario_id, "2026-03-09T03:59:59Z", 5),
        evento(casa_id, usuario_id, "2026-03-09T04:00:00Z", 7),
    ]

    ranking = servico.obter_ranking(
        casa_id, FiltroPeriodoScore(data_inicio="2026-03-08", data_fim="2026-03-09")
    )

    assert ranking["moradores"][0]["pontos"] == 8


def test_extrato_filtra_usuario_e_casa_e_pagina_em_ordem_estavel():
    servico, banco, casa_id, usuario_id = montar_servico()
    eventos = [
        evento(casa_id, usuario_id, "2026-09-01T12:00:00Z", 25),
        evento(casa_id, usuario_id, "2026-09-02T12:00:00Z", 50),
        evento(casa_id, usuario_id, "2026-09-02T12:00:00Z", -50),
    ]
    for indice, item in enumerate(eventos, start=1):
        item["id"] = str(UUID(int=indice))
    banco.registros["score_event"] = eventos + [
        evento(uuid4(), usuario_id, "2026-09-03T12:00:00Z", 999),
        evento(casa_id, uuid4(), "2026-09-03T12:00:00Z", 999),
    ]

    primeira = servico.obter_extrato(
        casa_id, FiltroExtratoScore(fk_usuario_id=usuario_id, limite=2)
    )
    segunda = servico.obter_extrato(
        casa_id, FiltroExtratoScore(fk_usuario_id=usuario_id, inicio=2, limite=2)
    )
    esgotada = servico.obter_extrato(
        casa_id, FiltroExtratoScore(fk_usuario_id=usuario_id, inicio=4, limite=2)
    )

    assert primeira["eventos"] == [eventos[2], eventos[1]]
    assert segunda["eventos"] == [eventos[0]]
    assert esgotada["eventos"] == []
    assert primeira["total"] == segunda["total"] == esgotada["total"] == 3


def test_ranking_sem_vinculos_e_extrato_sem_eventos_retornam_listas_vazias():
    servico, banco, casa_id, _ = montar_servico()
    banco.registros["pertencer"] = []

    assert servico.obter_ranking(casa_id, FiltroPeriodoScore())["moradores"] == []
    extrato = servico.obter_extrato(casa_id, FiltroExtratoScore())
    assert extrato["eventos"] == []
    assert extrato["total"] == 0
