"""Testes unitários do cálculo puro de score."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from services.score import ServicoScore


@pytest.fixture
def servico():
    return ServicoScore()


@pytest.fixture
def usuario_id():
    return uuid4()


@pytest.fixture
def data_fim():
    return datetime(2026, 10, 10, 12, tzinfo=timezone.utc)


def calcular(
    servico,
    usuario_id,
    data_fim,
    *,
    peso=1,
    prazo_dias=2,
    concluida_em=None,
    usuarios_atribuidos=None,
):
    return servico.calcular_score(
        peso=peso,
        prazo_dias=prazo_dias,
        data_fim=data_fim,
        concluida_em=concluida_em or data_fim,
        usuarios_atribuidos=(
            [usuario_id]
            if usuarios_atribuidos is None
            else usuarios_atribuidos
        ),
    )


@pytest.mark.parametrize(
    "peso,pontos_base",
    [(1, 10), (2, 25), (3, 50)],
)
def test_mapeia_peso_para_pontos_base(
    servico, usuario_id, data_fim, peso, pontos_base
):
    resultado = calcular(
        servico,
        usuario_id,
        data_fim,
        peso=peso,
    )

    assert resultado.usuario_id == usuario_id
    assert resultado.peso == peso
    assert resultado.pontos_base == pontos_base
    assert resultado.prazo_dias == 2
    assert resultado.pontos_finais == pontos_base


@pytest.mark.parametrize("peso", [0, 4, -1, 1.5, "1", True, None])
def test_rejeita_peso_fora_do_contrato(
    servico, usuario_id, data_fim, peso
):
    with pytest.raises(ValueError):
        calcular(servico, usuario_id, data_fim, peso=peso)


@pytest.mark.parametrize("prazo_dias", [0, -1, 1.5, "2", True, None])
def test_rejeita_prazo_que_nao_seja_inteiro_positivo(
    servico, usuario_id, data_fim, prazo_dias
):
    with pytest.raises(ValueError):
        calcular(servico, usuario_id, data_fim, prazo_dias=prazo_dias)


@pytest.mark.parametrize("diferenca", [timedelta(days=-2), timedelta(0)])
def test_conclusao_antecipada_ou_no_prazo_nao_desconta(
    servico, usuario_id, data_fim, diferenca
):
    resultado = calcular(
        servico,
        usuario_id,
        data_fim,
        peso=3,
        prazo_dias=5,
        concluida_em=data_fim + diferenca,
    )

    assert resultado.dias_atraso == 0
    assert resultado.desconto_total == Decimal("0")
    assert resultado.pontos_finais == 50


@pytest.mark.parametrize(
    "atraso,dias_atraso",
    [
        (timedelta(microseconds=1), 1),
        (timedelta(hours=23, minutes=59, seconds=59), 1),
        (timedelta(hours=24), 2),
        (timedelta(hours=47, minutes=59, seconds=59), 2),
        (timedelta(hours=48), 3),
    ],
)
def test_atraso_usa_faixas_iniciadas_de_vinte_e_quatro_horas(
    servico, usuario_id, data_fim, atraso, dias_atraso
):
    resultado = calcular(
        servico,
        usuario_id,
        data_fim,
        prazo_dias=5,
        concluida_em=data_fim + atraso,
    )

    assert resultado.dias_atraso == dias_atraso
    assert resultado.desconto_total == Decimal(2 * dias_atraso)
    assert resultado.pontos_finais == 10 - (2 * dias_atraso)


def test_pontuacao_chega_a_zero_e_nunca_fica_negativa(
    servico, usuario_id, data_fim
):
    no_limite = calcular(
        servico,
        usuario_id,
        data_fim,
        prazo_dias=2,
        concluida_em=data_fim + timedelta(hours=24),
    )
    muito_atrasada = calcular(
        servico,
        usuario_id,
        data_fim,
        prazo_dias=2,
        concluida_em=data_fim + timedelta(days=30),
    )

    assert no_limite.pontos_finais == 0
    assert muito_atrasada.pontos_finais == 0


def test_arredonda_meio_ponto_para_cima_apenas_no_resultado_final(
    servico, usuario_id, data_fim
):
    resultado = calcular(
        servico,
        usuario_id,
        data_fim,
        peso=2,
        prazo_dias=2,
        concluida_em=data_fim + timedelta(microseconds=1),
    )

    assert resultado.percentual_por_dia == Decimal("50")
    assert resultado.desconto_por_dia == Decimal("12.5")
    assert resultado.desconto_total == Decimal("12.5")
    assert resultado.pontos_finais == 13


def test_nao_arredonda_desconto_intermediario(
    servico, usuario_id, data_fim
):
    resultado = calcular(
        servico,
        usuario_id,
        data_fim,
        peso=2,
        prazo_dias=6,
        concluida_em=data_fim + timedelta(hours=72),
    )

    assert resultado.percentual_por_dia == Decimal(100) / Decimal(6)
    assert resultado.desconto_por_dia == Decimal(25) / Decimal(6)
    assert resultado.desconto_total == Decimal(25) / Decimal(6) * 4
    assert resultado.pontos_finais == 8


def test_calcula_resultado_final_pela_fracao_exata(
    servico, usuario_id, data_fim
):
    resultado = calcular(
        servico,
        usuario_id,
        data_fim,
        peso=1,
        prazo_dias=24,
        concluida_em=data_fim + timedelta(days=17),
    )

    assert resultado.dias_atraso == 18
    assert resultado.pontos_finais == 3


@pytest.mark.parametrize(
    "usuarios_atribuidos",
    [
        [],
        [uuid4(), uuid4()],
        (lambda usuario: [usuario, usuario])(uuid4()),
    ],
    ids=["sem-responsavel", "varios-responsaveis", "responsavel-duplicado"],
)
def test_exige_exatamente_um_responsavel(
    servico, usuario_id, data_fim, usuarios_atribuidos
):
    with pytest.raises(ValueError):
        calcular(
            servico,
            usuario_id,
            data_fim,
            usuarios_atribuidos=usuarios_atribuidos,
        )


def test_datas_sem_fuso_sao_interpretadas_como_utc(servico, usuario_id):
    data_fim_sem_fuso = datetime(2026, 10, 10, 12)
    concluida_sem_fuso = datetime(2026, 10, 11, 11)
    resultado_sem_fuso = calcular(
        servico,
        usuario_id,
        data_fim_sem_fuso,
        prazo_dias=3,
        concluida_em=concluida_sem_fuso,
    )
    resultado_utc = calcular(
        servico,
        usuario_id,
        data_fim_sem_fuso.replace(tzinfo=timezone.utc),
        prazo_dias=3,
        concluida_em=concluida_sem_fuso.replace(tzinfo=timezone.utc),
    )

    assert resultado_sem_fuso == resultado_utc


def test_datas_com_fusos_diferentes_representam_o_mesmo_instante(
    servico, usuario_id
):
    fuso_brasilia = timezone(timedelta(hours=-3))
    data_fim = datetime(2026, 10, 10, 12, tzinfo=fuso_brasilia)
    concluida_em = datetime(2026, 10, 10, 15, tzinfo=timezone.utc)

    resultado = calcular(
        servico,
        usuario_id,
        data_fim,
        concluida_em=concluida_em,
    )

    assert resultado.dias_atraso == 0
    assert resultado.pontos_finais == 10


def test_calculo_e_deterministico_e_resultado_e_imutavel(
    servico, usuario_id, data_fim
):
    argumentos = {
        "peso": 2,
        "prazo_dias": 3,
        "data_fim": data_fim,
        "concluida_em": data_fim + timedelta(hours=24),
        "usuarios_atribuidos": [usuario_id],
    }

    primeiro = servico.calcular_score(**argumentos)
    segundo = servico.calcular_score(**argumentos)

    assert primeiro == segundo
    with pytest.raises(FrozenInstanceError):
        primeiro.pontos_finais = 999
