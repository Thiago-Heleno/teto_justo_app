"""Testes unitários do serviço de casa."""

import base64
from types import SimpleNamespace
from unittest.mock import MagicMock, call
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from postgrest.exceptions import APIError

from schemas.casa import CasaAtualizar,  CasaCriar
from services.casa import ServicoCasa

@pytest.fixture
def consulta():
    consulta = MagicMock()
    consulta.insert.return_value = consulta
    consulta.select.return_value = consulta
    consulta.eq.return_value = consulta
    consulta.order.return_value = consulta
    consulta.range.return_value = consulta
    consulta.update.return_value = consulta
    consulta.delete.return_value = consulta
    consulta.in_.return_value = consulta
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
        "timezone": "America/Sao_Paulo",
    }

def test_criar_casa_insere_dados_com_foto_convertida(
    servico, banco, consulta, id_usuario, foto, registro_casa
):
    consulta.execute.return_value = SimpleNamespace(data=[registro_casa])

    dados = CasaCriar(
        nome="Casa Azul",
        endereco="Rua Tursi, 10",
        foto=foto["base64"],
    )

    resultado = servico.criar_casa(dados, id_usuario)

    assert resultado["nome"] == "Casa Azul"
    assert resultado["foto"] == foto["base64"]

    assert banco.table.call_args_list == [call("casa"), call("pertencer")]

    assert consulta.insert.call_args_list == [
        call({
            "nome": "Casa Azul",
            "endereco": "Rua Tursi, 10",
            "foto": foto["banco"],
            "timezone": "America/Sao_Paulo",
            "fk_usuario_id": str(id_usuario),
        }),
        call({
            "fk_usuario_id": str(id_usuario),
            "fk_casa_id": registro_casa["id"],
            "score": 0,
        }),
    ]

def test_criar_casa_sem_foto(
    servico, consulta, id_usuario, registro_casa
):
    registro_sem_foto = {**registro_casa, "foto": None}
    consulta.execute.return_value = SimpleNamespace(data=[registro_sem_foto])

    dados = CasaCriar(
        nome="Casa Azul",
        endereco="Rua Tursi, 10",
        foto=None,
    )

    resultado = servico.criar_casa(dados, id_usuario)

    assert resultado["foto"] is None

    assert consulta.insert.call_args_list[0] == call({
        "nome": "Casa Azul",
        "endereco": "Rua Tursi, 10",
        "foto": None,
        "timezone": "America/Sao_Paulo",
        "fk_usuario_id": str(id_usuario),
    })

def test_criar_casa_com_foto_base64_invalida_gera_400(
    servico, consulta, id_usuario
):
    dados = CasaCriar(
        nome="Casa Azul",
        endereco="Rua das Flores, 10",
        foto="%%%",
    )

    with pytest.raises(HTTPException) as erro:
        servico.criar_casa(dados, id_usuario)

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
    )

    with pytest.raises(HTTPException) as erro:
        servico.criar_casa(dados, id_usuario)

    assert erro.value.status_code == 500
    assert erro.value.detail == "Erro ao criar casa no banco."


def test_criar_casa_reverte_casa_se_vinculo_do_proprietario_falhar(
    servico, consulta, id_usuario, registro_casa
):
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_casa]),
        SimpleNamespace(data=[]),
        SimpleNamespace(data=[registro_casa]),
    ]

    with pytest.raises(HTTPException) as erro:
        servico.criar_casa(
            CasaCriar(nome="Casa Azul", endereco="Rua Tursi, 10"), id_usuario
        )

    assert erro.value.status_code == 500
    consulta.delete.assert_called_once_with()
    consulta.eq.assert_called_once_with("id", registro_casa["id"])


def test_criar_casa_rejeita_fuso_invalido():
    with pytest.raises(ValidationError):
        CasaCriar(
            nome="Casa Azul", endereco="Rua Tursi, 10", timezone="Fuso/Inexistente"
        )


def test_criar_casa_rejeita_proprietario_informado_pelo_cliente():
    with pytest.raises(ValidationError):
        CasaCriar(
            nome="Casa Azul",
            endereco="Rua das Flores, 10",
            fk_usuario_id=uuid4(),
        )

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

def test_listar_casas_filtra_usuario_e_pagina_apos_buscar_vinculos(
    servico, consulta, id_usuario, registro_casa, foto
):
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_casa]),
        SimpleNamespace(data=[]),
    ]

    resultado = servico.listar_casas(id_usuario, inicio=0, limite=1)

    assert len(resultado) == 1
    assert resultado[0]["nome"] == "Casa Azul"
    assert resultado[0]["foto"] == foto["base64"]

    assert consulta.eq.call_args_list == [
        call("fk_usuario_id", str(id_usuario)),
        call("fk_usuario_id", str(id_usuario)),
        call("ativo", True),
    ]
    assert consulta.order.call_args_list == [call("id"), call("fk_casa_id")]
    assert consulta.range.call_args_list == [call(0, 499), call(0, 499)]

def test_atualizar_casa_envia_apenas_campos_informados(
    servico, consulta, id_casa, id_usuario, registro_casa
):
    atualizado = {**registro_casa, "nome": "Casa Verde"}
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"fk_usuario_id": str(id_usuario)}]),
        SimpleNamespace(data=[atualizado]),
    ]

    resultado = servico.atualizar_casa(
        id_casa,
        CasaAtualizar(nome="Casa Verde"),
        id_usuario,
    )

    assert resultado["nome"] == "Casa Verde"
    consulta.update.assert_called_once_with({"nome": "Casa Verde"})
    assert consulta.eq.call_args_list == [
        call("id", str(id_casa)),
        call("id", str(id_casa)),
    ]

def test_atualizar_casa_converte_nova_foto(
    servico, consulta, id_casa, id_usuario, registro_casa
):
    nova_foto_bytes = b"nova fachada"
    nova_foto_base64 = base64.b64encode(nova_foto_bytes).decode("ascii")
    nova_foto_banco = "\\x" + nova_foto_bytes.hex()

    atualizado = {
        **registro_casa,
        "foto": nova_foto_banco,
    }
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"fk_usuario_id": str(id_usuario)}]),
        SimpleNamespace(data=[atualizado]),
    ]

    resultado = servico.atualizar_casa(
        id_casa,
        CasaAtualizar(foto=nova_foto_base64),
        id_usuario,
    )

    consulta.update.assert_called_once_with(
        {"foto": nova_foto_banco}
    )
    assert resultado["foto"] == nova_foto_base64


def test_atualizar_fuso_da_casa(
    servico, consulta, id_casa, id_usuario, registro_casa
):
    atualizado = {**registro_casa, "timezone": "UTC"}
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"fk_usuario_id": str(id_usuario)}]),
        SimpleNamespace(data=[atualizado]),
    ]

    resultado = servico.atualizar_casa(
        id_casa, CasaAtualizar(timezone="UTC"), id_usuario
    )

    assert resultado["timezone"] == "UTC"
    consulta.update.assert_called_once_with({"timezone": "UTC"})

def test_atualizar_casa_sem_dados_gera_400(
    servico, consulta, id_casa, id_usuario
):
    consulta.execute.return_value = SimpleNamespace(
        data=[{"fk_usuario_id": str(id_usuario)}]
    )
    with pytest.raises(HTTPException) as erro:
        servico.atualizar_casa(
            id_casa,
            CasaAtualizar(),
            id_usuario,
        )

    assert erro.value.status_code == 400
    assert erro.value.detail == "Nenhum dado para atualização."
    consulta.update.assert_not_called()

def test_atualizar_casa_inexistente_gera_404(
    servico, consulta, id_casa, id_usuario
):
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"fk_usuario_id": str(id_usuario)}]),
        SimpleNamespace(data=[]),
    ]

    with pytest.raises(HTTPException) as erro:
        servico.atualizar_casa(
            id_casa,
            CasaAtualizar(nome="Casa inexistente"),
            id_usuario,
        )

    assert erro.value.status_code == 404
    assert erro.value.detail == "Casa não encontrada."
    consulta.update.assert_called_once_with({"nome": "Casa inexistente"})

def test_excluir_casa_existente_retorna_true(
    servico, consulta, id_casa, id_usuario, registro_casa
):
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"fk_usuario_id": str(id_usuario)}]),
        SimpleNamespace(data=[registro_casa]),
    ]

    resultado = servico.excluir_casa(id_casa, id_usuario)

    assert resultado is True
    consulta.delete.assert_called_once_with()
    assert consulta.eq.call_args_list == [
        call("id", str(id_casa)),
        call("id", str(id_casa)),
    ]

def test_excluir_casa_inexistente_gera_404(
    servico, consulta, id_casa, id_usuario
):
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"fk_usuario_id": str(id_usuario)}]),
        SimpleNamespace(data=[]),
    ]

    with pytest.raises(HTTPException) as erro:
        servico.excluir_casa(id_casa, id_usuario)

    assert erro.value.status_code == 404
    assert erro.value.detail == "Casa não encontrada."
    consulta.delete.assert_called_once_with()


def test_excluir_casa_com_eventos_preserva_historico(
    servico, consulta, id_casa, id_usuario
):
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"fk_usuario_id": str(id_usuario)}]),
        APIError({"code": "23503", "message": "foreign key violation"}),
    ]

    with pytest.raises(HTTPException) as erro:
        servico.excluir_casa(id_casa, id_usuario)

    assert erro.value.status_code == 409


def test_morador_nao_pode_atualizar_casa(
    servico, consulta, id_casa, id_usuario
):
    consulta.execute.return_value = SimpleNamespace(
        data=[{"fk_usuario_id": str(uuid4())}]
    )

    with pytest.raises(HTTPException) as erro:
        servico.atualizar_casa(
            id_casa,
            CasaAtualizar(nome="Alteração proibida"),
            id_usuario,
        )

    assert erro.value.status_code == 403
    consulta.update.assert_not_called()


def test_morador_nao_pode_excluir_casa(
    servico, consulta, id_casa, id_usuario
):
    consulta.execute.return_value = SimpleNamespace(
        data=[{"fk_usuario_id": str(uuid4())}]
    )

    with pytest.raises(HTTPException) as erro:
        servico.excluir_casa(id_casa, id_usuario)

    assert erro.value.status_code == 403
    consulta.delete.assert_not_called()

def test_listar_moradores_retorna_usuarios_com_score(
    servico, banco, consulta, id_casa, registro_casa
):
    id_morador = uuid4()
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_casa]),
        SimpleNamespace(data=[{"fk_usuario_id": str(id_morador), "score": 15}]),
        SimpleNamespace(data=[{
            "id": str(id_morador), "nome": "Ana",
            "email": "ana@example.com", "telefone": None, "foto": None,
        }]),
    ]

    resultado = servico.listar_moradores(id_casa)

    assert resultado == [{
        "id": str(id_morador), "nome": "Ana", "email": "ana@example.com",
        "telefone": None, "foto": None, "score": 15,
    }]
    consulta.in_.assert_called_once_with("id", [str(id_morador)])

def test_listar_moradores_casa_inexistente_gera_404(servico, consulta, id_casa):
    consulta.execute.return_value = SimpleNamespace(data=[])

    with pytest.raises(HTTPException) as erro:
        servico.listar_moradores(id_casa)

    assert erro.value.status_code == 404

def test_listar_moradores_sem_vinculos_retorna_lista_vazia(
    servico, consulta, id_casa, registro_casa
):
    consulta.execute.side_effect = [
        SimpleNamespace(data=[registro_casa]),
        SimpleNamespace(data=[]),
    ]

    assert servico.listar_moradores(id_casa) == []
