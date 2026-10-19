"""Cadastro com verificação de e-mail: rotas com banco, e-mail e relógio simulados."""

import os
import re
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_KEY", "unit-test-placeholder")

from core.database import get_supabase  # noqa: E402
from main import app  # noqa: E402
from services.envio_email import ServicoEmail  # noqa: E402
from services.limite_login import get_limitador_verificacao  # noqa: E402


class BancoFalso:
    def __init__(self, usuarios=None):
        self.usuarios = usuarios or []
        self.inseridos = []

    def table(self, _nome):
        return ConsultaFalsa(self)


class ConsultaFalsa:
    def __init__(self, banco):
        self.banco = banco
        self.operacao = "select"
        self.email = None
        self.dados = None

    def select(self, _campos):
        return self

    def eq(self, _campo, valor):
        self.email = valor
        return self

    def insert(self, dados):
        self.operacao = "insert"
        self.dados = dados
        return self

    def execute(self):
        if self.operacao == "insert":
            registro = {"id": "11111111-1111-1111-1111-111111111111", **self.dados}
            self.banco.inseridos.append(registro)
            return SimpleNamespace(data=[registro])
        return SimpleNamespace(
            data=[u for u in self.banco.usuarios if u["email"] == self.email]
        )


@pytest.fixture
def ambiente(monkeypatch):
    monkeypatch.setenv("CASA_CONVITE_SECRET", "chave-de-testes-com-mais-de-trinta-e-dois-bytes")
    enviados = []

    def enviar_falso(_self, para, assunto, html):
        enviados.append({"para": para, "assunto": assunto, "html": html})

    monkeypatch.setattr(ServicoEmail, "enviar", enviar_falso)
    banco = BancoFalso()
    app.dependency_overrides[get_supabase] = lambda: banco
    limitador = get_limitador_verificacao.__wrapped__()  # instância nova, mesma configuração
    app.dependency_overrides[get_limitador_verificacao] = lambda: limitador
    with TestClient(app, raise_server_exceptions=False) as cliente:
        yield SimpleNamespace(cliente=cliente, banco=banco, enviados=enviados)
    app.dependency_overrides.clear()


def _dados(**extra):
    return {"nome": "Moradora", "email": "moradora@example.com", "senha": "Senha-123!", **extra}


def _solicitar(ambiente, **extra):
    resposta = ambiente.cliente.post("/usuarios/codigo-verificacao", json=_dados(**extra))
    assert resposta.status_code == 200, resposta.text
    codigo = re.search(r">(\d{5})</p>", ambiente.enviados[-1]["html"]).group(1)
    return codigo, resposta.json()["token_verificacao"]


def test_solicitar_envia_o_codigo_por_email_ao_cadastrante(ambiente):
    codigo, token = _solicitar(ambiente)

    assert [e["para"] for e in ambiente.enviados] == ["moradora@example.com"]
    assert "Teto Justo" in ambiente.enviados[0]["assunto"]
    assert token not in ambiente.enviados[0]["html"]
    assert len(codigo) == 5


def test_solicitar_com_email_ja_cadastrado_retorna_400_sem_enviar(ambiente):
    ambiente.banco.usuarios.append({"email": "moradora@example.com"})

    resposta = ambiente.cliente.post("/usuarios/codigo-verificacao", json=_dados())

    assert resposta.status_code == 400
    assert ambiente.enviados == []


def test_solicitar_valida_os_dados_antes_de_enviar(ambiente):
    resposta = ambiente.cliente.post(
        "/usuarios/codigo-verificacao", json=_dados(email="invalido")
    )

    assert resposta.status_code == 422
    assert ambiente.enviados == []


def test_falha_no_envio_retorna_503_e_nao_gasta_tentativa(ambiente, monkeypatch):
    def falhar(_self, *_args):
        raise HTTPException(status_code=503, detail="Não foi possível enviar o email.")

    monkeypatch.setattr(ServicoEmail, "enviar", falhar)

    for _ in range(8):
        resposta = ambiente.cliente.post("/usuarios/codigo-verificacao", json=_dados())
        assert resposta.status_code == 503


def test_limite_de_envios_por_email_retorna_429(ambiente):
    for _ in range(5):
        ambiente.cliente.post("/usuarios/codigo-verificacao", json=_dados())

    resposta = ambiente.cliente.post("/usuarios/codigo-verificacao", json=_dados())

    assert resposta.status_code == 429
    assert "Retry-After" in resposta.headers
    assert "login" not in resposta.json()["detail"]


def test_cadastro_com_codigo_correto_cria_o_usuario(ambiente):
    codigo, token = _solicitar(ambiente)

    resposta = ambiente.cliente.post(
        "/usuarios/", json=_dados(codigo=codigo, token_verificacao=token)
    )

    assert resposta.status_code == 201, resposta.text
    assert [u["email"] for u in ambiente.banco.inseridos] == ["moradora@example.com"]
    assert "senha" not in resposta.json()
    assert "codigo" not in ambiente.banco.inseridos[0]


def test_cadastro_sem_codigo_ou_com_formato_invalido_retorna_422(ambiente):
    _, token = _solicitar(ambiente)

    sem_codigo = ambiente.cliente.post("/usuarios/", json=_dados())
    formato = ambiente.cliente.post(
        "/usuarios/", json=_dados(codigo="12a45", token_verificacao=token)
    )

    assert sem_codigo.status_code == formato.status_code == 422
    assert ambiente.banco.inseridos == []


def test_cadastro_com_codigo_errado_ou_de_outro_email_retorna_400(ambiente):
    codigo, token = _solicitar(ambiente)
    errado = "10000" if codigo != "10000" else "10001"

    resposta_errado = ambiente.cliente.post(
        "/usuarios/", json=_dados(codigo=errado, token_verificacao=token)
    )
    resposta_outro = ambiente.cliente.post(
        "/usuarios/",
        json=_dados(email="outra@example.com", codigo=codigo, token_verificacao=token),
    )

    assert resposta_errado.status_code == resposta_outro.status_code == 400
    assert resposta_errado.json()["detail"] == "Código inválido ou expirado."
    assert ambiente.banco.inseridos == []


def test_tentativas_erradas_bloqueiam_ate_o_codigo_correto(ambiente):
    codigo, token = _solicitar(ambiente)
    errado = "10000" if codigo != "10000" else "10001"
    corpo_errado = _dados(codigo=errado, token_verificacao=token)

    status = [ambiente.cliente.post("/usuarios/", json=corpo_errado).status_code for _ in range(5)]
    correto = ambiente.cliente.post(
        "/usuarios/", json=_dados(codigo=codigo, token_verificacao=token)
    )

    assert status == [400, 400, 400, 400, 429]
    assert correto.status_code == 429
    assert ambiente.banco.inseridos == []
