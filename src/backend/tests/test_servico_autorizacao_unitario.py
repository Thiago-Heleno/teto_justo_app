"""Testes unitários de cargo e autorização por casa."""

from types import SimpleNamespace
from unittest.mock import MagicMock, call
from uuid import uuid4

import pytest
from fastapi import HTTPException

from services.autorizacao import ServicoAutorizacaoCasa, papel_na_casa


@pytest.mark.parametrize("usuario_texto,proprietario_texto", [
    (False, False), (False, True), (True, False), (True, True),
])
@pytest.mark.parametrize("proprietario,vinculo_ativo,esperado", [
    (True, True, "administrador"),
    (True, False, "administrador"),
    (False, True, "morador"),
    (False, False, "nenhum"),
])
def test_papel_depende_da_propriedade_e_do_vinculo_ativo(
    usuario_texto, proprietario_texto, proprietario, vinculo_ativo, esperado,
):
    id_usuario = uuid4()
    id_proprietario = id_usuario if proprietario else uuid4()

    assert papel_na_casa(
        str(id_usuario) if usuario_texto else id_usuario,
        str(id_proprietario) if proprietario_texto else id_proprietario,
        vinculo_ativo,
    ) == esperado


@pytest.fixture
def consulta():
    consulta = MagicMock()
    consulta.select.return_value = consulta
    consulta.eq.return_value = consulta
    consulta.limit.return_value = consulta
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

    resultado = servico.garantir_administrador_da_casa(id_casa, id_usuario)

    assert resultado == str(id_usuario)
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


@pytest.mark.parametrize("operacao", ["garantir_acesso", "garantir_administrador_da_casa"])
def test_casa_inexistente_recebe_404(servico, consulta, operacao):
    consulta.execute.return_value = SimpleNamespace(data=[])

    with pytest.raises(HTTPException) as erro:
        getattr(servico, operacao)(uuid4(), uuid4())

    assert erro.value.status_code == 404
    assert erro.value.detail == "Casa não encontrada."


def test_proprietario_acessa_sem_consultar_vinculo(servico, consulta):
    id_usuario = uuid4()
    consulta.execute.return_value = SimpleNamespace(
        data=[{"fk_usuario_id": str(id_usuario)}]
    )

    servico.garantir_acesso(uuid4(), id_usuario)

    consulta.execute.assert_called_once()
    servico.supabase.table.assert_called_once_with("casa")


def test_morador_acessa_somente_com_vinculo_ativo_na_casa(servico, consulta):
    id_casa, id_usuario = uuid4(), uuid4()
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"fk_usuario_id": str(uuid4())}]),
        SimpleNamespace(data=[{"fk_usuario_id": str(id_usuario)}]),
    ]

    servico.garantir_acesso(id_casa, id_usuario)

    assert servico.supabase.table.call_args_list == [call("casa"), call("pertencer")]
    assert consulta.eq.call_args_list == [
        call("id", str(id_casa)),
        call("fk_casa_id", str(id_casa)),
        call("fk_usuario_id", str(id_usuario)),
        call("ativo", True),
    ]


def test_usuario_sem_vinculo_ativo_recebe_403(servico, consulta):
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"fk_usuario_id": str(uuid4())}]),
        SimpleNamespace(data=[]),
    ]

    with pytest.raises(HTTPException) as erro:
        servico.garantir_acesso(uuid4(), uuid4())

    assert erro.value.status_code == 403
    assert erro.value.detail == "Acesso restrito aos moradores da casa."
