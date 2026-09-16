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
        "endereco": "Rua Tursi, 10",
        "foto": foto["banco"],
        "fk_usuario_id": str(id_usuario),
    }

def test_criar_casa_insere_dados_com_foto_convertida(
    servico, banco, consulta, id_usuario, foto, registro_casa
):
    consulta.execute.return_value = SimpleNamespace(data=[registro_casa])

    dados = CasaCriar(
        nome="Casa Azul",
        endereco="Rua Tursi, 10",
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
            "endereco": "Rua Tursi, 10",
            "foto": foto["banco"],
            "fk_usuario_id": str(id_usuario),
        }
    )

def test_criar_casa_sem_foto(
    servico, consulta, id_usuario, registro_casa
):
    registro_sem_foto = {**registro_casa, "foto": None}
    consulta.execute.return_value = SimpleNamespace(data=[registro_sem_foto])

    dados = CasaCriar(
        nome="Casa Azul",
        endereco="Rua Tursi, 10",
        foto=None,
        fk_usuario_id=id_usuario,
    )

    resultado = servico.criar_casa(dados)

    assert resultado["foto"] is None

    consulta.insert.assert_called_once_with(
        {
            "nome": "Casa Azul",
            "endereco": "Rua Tursi, 10",
            "foto": None,
            "fk_usuario_id": str(id_usuario),
        }
    )

def test_criar_casa_com_foto_base64_invalida_gera_400(
    servico, consulta, id_usuario
):
    dados = CasaCriar(
        nome="Casa Azul",
        endereco="Rua das Flores, 10",
        foto="%%%",
        fk_usuario_id=id_usuario,
    )

    with pytest.raises(HTTPException) as erro:
        servico.criar_casa(dados)

    assert erro.value.status_code == 400
    assert erro.value.detail == "A foto deve estar em Base64 válido."
    consulta.insert.assert_not_called()

def test_criar_casa_sem_retorno_do_banco_gera_500(
    servico, consulta, id_usuario
):
    consulta.execute.return_value = SimpleNamespace(data=[])

    dados = CasaCriar(
        nome="Casa Azul",
        endereco="Rua das Flores, 10",
        fk_usuario_id=id_usuario,
    )

    with pytest.raises(HTTPException) as erro:
        servico.criar_casa(dados)

    assert erro.value.status_code == 500
    assert erro.value.detail == "Erro ao criar casa no banco."

def test_buscar_casa_por_id(
    servico, consulta, id_casa, registro_casa, foto
):
    consulta.execute.return_value = SimpleNamespace(data=[registro_casa])

    resultado = servico.buscar_casa(id_casa)

    assert resultado["id"] == registro_casa["id"]
    assert resultado["nome"] == "Casa Azul"
    assert resultado["foto"] == foto["base64"]

    consulta.select.assert_called_once_with("*")
    consulta.eq.assert_called_once_with("id", str(id_casa))

def test_buscar_casa_inexistente_gera_404(
    servico, consulta, id_casa
):
    consulta.execute.return_value = SimpleNamespace(data=[])

    with pytest.raises(HTTPException) as erro:
        servico.buscar_casa(id_casa)

    assert erro.value.status_code == 404
    assert erro.value.detail == "Casa não encontrada."

def test_buscar_casa_com_foto_invalida_no_banco_gera_500(
    servico, consulta, id_casa, registro_casa
):
    registro_invalido = {**registro_casa, "foto": "\\xzz"}
    consulta.execute.return_value = SimpleNamespace(data=[registro_invalido])

    with pytest.raises(HTTPException) as erro:
        servico.buscar_casa(id_casa)

    assert erro.value.status_code == 500
    assert erro.value.detail == "Formato de foto inválido no banco."

def test_listar_casas_aplica_intervalo_inclusivo(
    servico, consulta, registro_casa, foto
):
    consulta.execute.return_value = SimpleNamespace(data=[registro_casa])

    resultado = servico.listar_casas(inicio=10, limite=25)

    assert len(resultado) == 1
    assert resultado[0]["nome"] == "Casa Azul"
    assert resultado[0]["foto"] == foto["base64"]

    consulta.range.assert_called_once_with(10, 34)