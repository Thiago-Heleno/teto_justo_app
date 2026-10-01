from uuid import uuid4

import pytest
from pydantic import ValidationError

from schemas.rotatividade import RotatividadeCriar


@pytest.fixture
def payload():
    return {
        "fk_casa_id": uuid4(),
        "nome": "Limpar cozinha",
        "descricao": "",
        "peso": 2,
        "prazo_dias": 3,
        "atraso_maximo": 2,
        "modo_prazo": "intervalo",
        "participantes": [uuid4(), uuid4()],
        "dias_semana": [4, 1],
        "intervalo_semanas": 2,
    }


def test_contrato_normaliza_dias_semana_e_preserva_ordem_dos_participantes(payload):
    dados = RotatividadeCriar(**payload)

    assert dados.dias_semana == [1, 4]
    assert dados.participantes == payload["participantes"]


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("peso", 4),
        ("prazo_dias", 6),
        ("atraso_maximo", 0),
        ("participantes", []),
        ("dias_semana", []),
        ("dias_semana", [1, 1]),
        ("intervalo_semanas", 5),
    ],
)
def test_contrato_rejeita_configuracao_invalida(payload, campo, valor):
    with pytest.raises(ValidationError):
        RotatividadeCriar(**{**payload, campo: valor})


def test_contrato_rejeita_participantes_duplicados(payload):
    participante = uuid4()
    with pytest.raises(ValidationError):
        RotatividadeCriar(**{**payload, "participantes": [participante, participante]})


def test_contrato_rejeita_campos_nao_esperados(payload):
    with pytest.raises(ValidationError):
        RotatividadeCriar(**{**payload, "fk_usuario_id": uuid4()})
