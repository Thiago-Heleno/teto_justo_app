"""Testes unitários da autorização de administrador por casa."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from services.autorizacao import ServicoAutorizacaoCasa


@pytest.fixture
def consulta():
    consulta = MagicMock()
    consulta.select.return_value = consulta
    consulta.eq.return_value = consulta
    return consulta


@pytest.fixture
def servico(consulta):
    banco = MagicMock()
    banco.table.return_value = consulta
    return ServicoAutorizacaoCasa(banco)


def test_proprietario_e_administrador_da_casa(servico, consulta):
    id_casa = uuid4()
    id_usuario = uuid4()
    consulta.execute.return_value = SimpleNamespace(
        data=[{"fk_usuario_id": str(id_usuario)}]
    )

    servico.garantir_administrador_da_casa(id_casa, id_usuario)

    consulta.select.assert_called_once_with("fk_usuario_id")
    consulta.eq.assert_called_once_with("id", str(id_casa))


def test_morador_recebe_403(servico, consulta):
    consulta.execute.return_value = SimpleNamespace(
        data=[{"fk_usuario_id": str(uuid4())}]
    )

    with pytest.raises(HTTPException) as erro:
        servico.garantir_administrador_da_casa(uuid4(), uuid4())

    assert erro.value.status_code == 403
    assert erro.value.detail == (
        "Permissão de administrador necessária para esta casa."
    )


def test_casa_inexistente_recebe_404(servico, consulta):
    consulta.execute.return_value = SimpleNamespace(data=[])

    with pytest.raises(HTTPException) as erro:
        servico.garantir_administrador_da_casa(uuid4(), uuid4())

    assert erro.value.status_code == 404
    assert erro.value.detail == "Casa não encontrada."
