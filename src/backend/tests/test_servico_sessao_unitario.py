"""Testes unitários do serviço de sessão."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from schemas.sessao import SessaoAtualizar, SessaoCriar
from services.sessao import ServicoSessao


@pytest.fixture
def consulta():
    consulta = MagicMock()
    consulta.insert.return_value = consulta
    consulta.select.return_value = consulta
    consulta.eq.return_value = consulta
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
    return ServicoSessao(banco)


@pytest.fixture
def id_sessao():
    return uuid4()


@pytest.fixture
def registro_sessao(id_sessao):
    return {
        "id": str(id_sessao),
        "token": "token-original",
        "criado_em": "2026-09-15T12:00:00Z",
        "expira_em": "2026-10-01T12:00:00Z",
        "fk_usuario_id": str(uuid4()),
    }


def test_criar_sessao_insere_dados_serializados(
    servico, banco, consulta, registro_sessao
):
    consulta.execute.return_value = SimpleNamespace(data=[registro_sessao])
    dados = SessaoCriar(
        token="token-original",
        expira_em=datetime(2026, 10, 1, 12, tzinfo=timezone.utc),
        fk_usuario_id=registro_sessao["fk_usuario_id"],
    )

    resultado = servico.criar_sessao(dados)

    assert resultado == registro_sessao
    banco.table.assert_called_once_with("sessao")
    consulta.insert.assert_called_once_with(
        {
            "token": "token-original",
            "expira_em": "2026-10-01T12:00:00Z",
            "fk_usuario_id": registro_sessao["fk_usuario_id"],
        }
    )


def test_criar_sessao_sem_retorno_do_banco_gera_500(servico, consulta):
    consulta.execute.return_value = SimpleNamespace(data=[])
    dados = SessaoCriar(
        token="token",
        expira_em=datetime(2026, 10, 1, tzinfo=timezone.utc),
        fk_usuario_id=uuid4(),
    )

    with pytest.raises(HTTPException) as erro:
        servico.criar_sessao(dados)

    assert erro.value.status_code == 500
    assert erro.value.detail == "Erro ao criar sessão no banco."


def test_buscar_sessao_por_id(servico, consulta, id_sessao, registro_sessao):
    consulta.execute.return_value = SimpleNamespace(data=[registro_sessao])

    resultado = servico.buscar_sessao(id_sessao)

    assert resultado == registro_sessao
    consulta.select.assert_called_once_with("*")
    consulta.eq.assert_called_once_with("id", str(id_sessao))


def test_buscar_sessao_inexistente_gera_404(servico, consulta, id_sessao):
    consulta.execute.return_value = SimpleNamespace(data=[])

    with pytest.raises(HTTPException) as erro:
        servico.buscar_sessao(id_sessao)

    assert erro.value.status_code == 404
    assert erro.value.detail == "Sessão não encontrada."


def test_listar_sessoes_aplica_intervalo_inclusivo(
    servico, consulta, registro_sessao
):
    consulta.execute.return_value = SimpleNamespace(data=[registro_sessao])

    resultado = servico.listar_sessoes(inicio=10, limite=25)

    assert resultado == [registro_sessao]
    consulta.range.assert_called_once_with(10, 34)


def test_atualizar_sessao_envia_apenas_campos_informados(
    servico, consulta, id_sessao, registro_sessao
):
    atualizado = {**registro_sessao, "token": "token-novo"}
    consulta.execute.return_value = SimpleNamespace(data=[atualizado])

    resultado = servico.atualizar_sessao(
        id_sessao,
        SessaoAtualizar(token="token-novo"),
    )

    assert resultado == atualizado
    consulta.update.assert_called_once_with({"token": "token-novo"})
    consulta.eq.assert_called_once_with("id", str(id_sessao))


def test_atualizar_sessao_sem_dados_gera_400(servico, consulta, id_sessao):
    with pytest.raises(HTTPException) as erro:
        servico.atualizar_sessao(id_sessao, SessaoAtualizar())

    assert erro.value.status_code == 400
    assert erro.value.detail == "Nenhum dado para atualização."
    consulta.update.assert_not_called()


def test_atualizar_sessao_inexistente_gera_404(servico, consulta, id_sessao):
    consulta.execute.return_value = SimpleNamespace(data=[])

    with pytest.raises(HTTPException) as erro:
        servico.atualizar_sessao(id_sessao, SessaoAtualizar(token="novo"))

    assert erro.value.status_code == 404


def test_excluir_sessao_existente_retorna_true(
    servico, consulta, id_sessao, registro_sessao
):
    consulta.execute.return_value = SimpleNamespace(data=[registro_sessao])

    resultado = servico.excluir_sessao(id_sessao)

    assert resultado is True
    consulta.delete.assert_called_once_with()
    consulta.eq.assert_called_once_with("id", str(id_sessao))


def test_excluir_sessao_inexistente_gera_404(servico, consulta, id_sessao):
    consulta.execute.return_value = SimpleNamespace(data=[])

    with pytest.raises(HTTPException) as erro:
        servico.excluir_sessao(id_sessao)

    assert erro.value.status_code == 404
