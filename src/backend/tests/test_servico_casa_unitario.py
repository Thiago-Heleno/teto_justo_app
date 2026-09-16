"""Testes unitários do serviço de casa."""

import base64
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest 
from fastapi import HTTPException

from schemas.casa import CasaAtualizar,  CasaCriar
from services.casa import ServicoCasa

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
    return ServicoCasa(banco)

@pytest.fixture
def id_casa():
    return uuid4()


@pytest.fixture
def id_usuario():
    return uuid4()


@pytest.fixture
def foto():
    conteudo = b"fachada da casa"
    return {
        "bytes": conteudo,
        "base64": base64.b64encode(conteudo).decode("ascii"),
        "banco": "\\x" + conteudo.hex(),
    }


@pytest.fixture
def registro_casa(id_casa, id_usuario, foto):
    return {
        "id": str(id_casa),
        "nome": "Casa Azul",
        "endereco": "Rua das Flores, 10",
        "foto": foto["banco"],
        "fk_usuario_id": str(id_usuario),
    }

def test_criar_casa_insere_dados_com_foto_convertida(
    servico, banco, consulta, id_usuario, foto, registro_casa
):
    consulta.execute.return_value = SimpleNamespace(data=[registro_casa])

    dados = CasaCriar(
        nome="Casa Azul",
        endereco="Rua das Flores, 10",
        foto=foto["base64"],
        fk_usuario_id=id_usuario,
    )

    resultado = servico.criar_casa(dados)

    assert resultado["nome"] == "Casa Azul"
    assert resultado["foto"] == foto["base64"]

    banco.table.assert_called_once_with("casa")

    consulta.insert.assert_called_once_with(
        {
            "nome": "Casa Azul",
            "endereco": "Rua das Flores, 10",
            "foto": foto["banco"],
            "fk_usuario_id": str(id_usuario),
        }
    )