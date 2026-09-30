"""Testes unitários de login e logout, com cliente Supabase simulado."""

import secrets
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import bcrypt
import pytest
from fastapi import HTTPException

from schemas.sessao import LoginEntrada
from services.sessao import ServicoSessao, hash_token_sessao


@pytest.fixture(scope="module")
def credencial():
    senha = secrets.token_urlsafe(24)
    return senha, bcrypt.hashpw(senha.encode(), bcrypt.gensalt(rounds=4)).decode()


@pytest.fixture
def consulta():
    consulta = MagicMock()
    for metodo in ("insert", "select", "eq", "limit", "delete"):
        getattr(consulta, metodo).return_value = consulta
    return consulta


@pytest.fixture
def servico(consulta):
    banco = MagicMock()
    banco.table.return_value = consulta
    return ServicoSessao(banco)


def test_login_valida_bcrypt_e_armazena_somente_hash(servico, consulta, credencial):
    senha, senha_hash = credencial
    usuario_id = str(uuid4())
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"id": usuario_id, "senha_hash": senha_hash}]),
        SimpleNamespace(data=[{"id": str(uuid4())}]),
    ]
    antes = datetime.now(timezone.utc)

    resposta = servico.login(LoginEntrada(email="morador@example.com", senha=senha))

    gravado = consulta.insert.call_args.args[0]
    assert gravado["fk_usuario_id"] == usuario_id
    assert gravado["token"] == hash_token_sessao(resposta.token)
    assert gravado["token"] != resposta.token
    assert len(resposta.token) >= 43
    assert antes + timedelta(hours=24) <= resposta.expira_em
    assert resposta.expira_em <= datetime.now(timezone.utc) + timedelta(hours=24)
    assert set(resposta.model_dump()) == {"token", "expira_em"}


@pytest.mark.parametrize(
    "cenario", ["ausente", "incorreta", "sem_hash", "hash_invalido", "duplicado"]
)
def test_login_invalido_nao_cria_sessao(servico, consulta, credencial, cenario):
    senha, senha_hash = credencial
    usuarios = [{"id": str(uuid4()), "senha_hash": senha_hash}]
    if cenario == "ausente":
        usuarios = []
    elif cenario == "incorreta":
        senha = secrets.token_urlsafe(24)
    elif cenario == "sem_hash":
        usuarios[0]["senha_hash"] = None
    elif cenario == "hash_invalido":
        usuarios[0]["senha_hash"] = "formato-invalido"
    elif cenario == "duplicado":
        usuarios.append(dict(usuarios[0]))
    consulta.execute.return_value = SimpleNamespace(data=usuarios)

    with pytest.raises(HTTPException) as erro:
        servico.login(LoginEntrada(email="morador@example.com", senha=senha))

    assert erro.value.status_code == 401
    assert erro.value.detail == "E-mail ou senha inválidos."
    assert erro.value.headers == {"WWW-Authenticate": "Bearer"}
    consulta.insert.assert_not_called()


def test_senha_multibyte_acima_de_72_bytes_nao_gera_500(servico, consulta, credencial):
    consulta.execute.return_value = SimpleNamespace(
        data=[{"id": str(uuid4()), "senha_hash": credencial[1]}]
    )
    with pytest.raises(HTTPException) as erro:
        servico.login(LoginEntrada(email="morador@example.com", senha="á" * 37))
    assert erro.value.status_code == 401
    consulta.insert.assert_not_called()


def test_login_sem_persistencia_nao_entrega_token(servico, consulta, credencial):
    senha, senha_hash = credencial
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"id": str(uuid4()), "senha_hash": senha_hash}]),
        SimpleNamespace(data=[]),
    ]
    with pytest.raises(HTTPException) as erro:
        servico.login(LoginEntrada(email="morador@example.com", senha=senha))
    assert erro.value.status_code == 500


def test_login_nao_converte_falha_de_infraestrutura_em_401(servico, consulta, credencial):
    consulta.execute.side_effect = RuntimeError("falha simulada")
    with pytest.raises(RuntimeError):
        servico.login(LoginEntrada(email="morador@example.com", senha=credencial[0]))


def test_logout_limita_exclusao_ao_token_e_usuario(servico, consulta):
    token = secrets.token_urlsafe(32)
    usuario_id = uuid4()

    servico.logout(token, usuario_id)

    consulta.delete.assert_called_once_with()
    assert consulta.eq.call_args_list[0].args == ("token", hash_token_sessao(token))
    assert consulta.eq.call_args_list[1].args == ("fk_usuario_id", str(usuario_id))
