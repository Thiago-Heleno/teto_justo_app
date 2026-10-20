"""Recuperação de senha: rotas com banco, e-mail e relógio simulados."""

import os
import re
from types import SimpleNamespace

import bcrypt
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
from services.limite_login import get_limitador_recuperacao  # noqa: E402
from services.verificacao_email import ServicoVerificacaoEmail  # noqa: E402


_EMAIL = "moradora@example.com"
_SENHA_ANTIGA = "Senha-antiga-1"
_SENHA_NOVA = "Senha-nova-123!"


def _hash(senha):
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt(rounds=4)).decode()


class BancoFalso:
    def __init__(self, usuarios, sessoes):
        self.tabelas = {"usuario": usuarios, "sessao": sessoes}

    def table(self, nome):
        return ConsultaFalsa(self.tabelas[nome])


class ConsultaFalsa:
    def __init__(self, linhas):
        self.linhas = linhas
        self.operacao = "select"
        self.filtros = {}
        self.dados = None

    def select(self, _campos):
        return self

    def update(self, dados):
        self.operacao, self.dados = "update", dados
        return self

    def delete(self):
        self.operacao = "delete"
        return self

    def eq(self, campo, valor):
        self.filtros[campo] = valor
        return self

    def execute(self):
        alvo = [
            linha for linha in self.linhas
            if all(linha.get(c) == v for c, v in self.filtros.items())
        ]
        if self.operacao == "update":
            for linha in alvo:
                linha.update(self.dados)
        elif self.operacao == "delete":
            for linha in alvo:
                self.linhas.remove(linha)
        return SimpleNamespace(data=alvo)


@pytest.fixture
def ambiente(monkeypatch):
    monkeypatch.setenv("CASA_CONVITE_SECRET", "chave-de-testes-com-mais-de-trinta-e-dois-bytes")
    enviados = []

    def enviar_falso(_self, para, assunto, html):
        enviados.append({"para": para, "assunto": assunto, "html": html})

    monkeypatch.setattr(ServicoEmail, "enviar", enviar_falso)
    usuarios = [
        {"id": "u1", "email": _EMAIL, "senha_hash": _hash(_SENHA_ANTIGA)},
        {"id": "u2", "email": "outra@example.com", "senha_hash": _hash("Outra-senha-1")},
        {"id": "u3", "email": "removida@example.com", "senha_hash": None},
    ]
    sessoes = [{"fk_usuario_id": "u1"}, {"fk_usuario_id": "u1"}, {"fk_usuario_id": "u2"}]
    banco = BancoFalso(usuarios, sessoes)
    app.dependency_overrides[get_supabase] = lambda: banco
    limitador = get_limitador_recuperacao.__wrapped__()  # instância nova, mesma configuração
    app.dependency_overrides[get_limitador_recuperacao] = lambda: limitador
    with TestClient(app, raise_server_exceptions=False) as cliente:
        yield SimpleNamespace(
            cliente=cliente, usuarios=usuarios, sessoes=sessoes, enviados=enviados
        )
    app.dependency_overrides.clear()


def _recuperar(ambiente, email=_EMAIL):
    return ambiente.cliente.post("/usuarios/recuperar-senha", json={"email": email})


def _codigo_enviado(ambiente):
    return re.search(r">(\d{5})</p>", ambiente.enviados[-1]["html"]).group(1)


def _redefinir(ambiente, codigo, token, email=_EMAIL, senha=_SENHA_NOVA):
    return ambiente.cliente.post(
        "/usuarios/redefinir-senha",
        json={"email": email, "codigo": codigo, "token_verificacao": token, "nova_senha": senha},
    )


def _senha_confere(ambiente, senha, id_usuario="u1"):
    usuario = next(u for u in ambiente.usuarios if u["id"] == id_usuario)
    return bcrypt.checkpw(senha.encode(), usuario["senha_hash"].encode())


def test_recuperar_envia_o_codigo_so_para_o_email_da_conta(ambiente):
    resposta = _recuperar(ambiente)

    assert resposta.status_code == 200, resposta.text
    assert set(resposta.json()) == {"token_verificacao", "expira_em"}
    assert [e["para"] for e in ambiente.enviados] == [_EMAIL]
    assert "Redefina sua senha" in ambiente.enviados[0]["html"]
    assert resposta.json()["token_verificacao"] not in ambiente.enviados[0]["html"]


@pytest.mark.parametrize("email", ["ninguem@example.com", "removida@example.com"])
def test_recuperar_nao_revela_se_a_conta_existe_nem_envia_email(ambiente, email):
    resposta = _recuperar(ambiente, email)

    assert resposta.status_code == 200
    assert set(resposta.json()) == {"token_verificacao", "expira_em"}
    assert ambiente.enviados == []


def test_falha_no_envio_retorna_503_e_nao_gasta_tentativa(ambiente, monkeypatch):
    def falhar(_self, *_args):
        raise HTTPException(status_code=503, detail="Não foi possível enviar o email.")

    monkeypatch.setattr(ServicoEmail, "enviar", falhar)

    for _ in range(8):
        assert _recuperar(ambiente).status_code == 503


def test_limite_de_pedidos_por_email_retorna_429(ambiente):
    for _ in range(5):
        _recuperar(ambiente)

    resposta = _recuperar(ambiente)

    assert resposta.status_code == 429
    assert "Retry-After" in resposta.headers
    assert "recuperação" in resposta.json()["detail"]


def test_redefinir_troca_a_senha_e_encerra_so_as_sessoes_da_conta(ambiente):
    token = _recuperar(ambiente).json()["token_verificacao"]

    resposta = _redefinir(ambiente, _codigo_enviado(ambiente), token)

    assert resposta.status_code == 204, resposta.text
    assert _senha_confere(ambiente, _SENHA_NOVA)
    assert not _senha_confere(ambiente, _SENHA_ANTIGA)
    assert ambiente.sessoes == [{"fk_usuario_id": "u2"}]


def test_codigo_so_vale_uma_vez(ambiente):
    token = _recuperar(ambiente).json()["token_verificacao"]
    codigo = _codigo_enviado(ambiente)
    assert _redefinir(ambiente, codigo, token).status_code == 204

    de_novo = _redefinir(ambiente, codigo, token, senha="Outra-nova-456!")

    assert de_novo.status_code == 400
    assert _senha_confere(ambiente, _SENHA_NOVA)


def test_codigo_de_cadastro_nao_redefine_senha(ambiente):
    emitido = ServicoVerificacaoEmail().emitir(_EMAIL)

    resposta = _redefinir(ambiente, emitido["codigo"], emitido["token_verificacao"])

    assert resposta.status_code == 400
    assert _senha_confere(ambiente, _SENHA_ANTIGA)


def test_codigo_errado_ou_de_outra_conta_retorna_400(ambiente):
    token = _recuperar(ambiente).json()["token_verificacao"]
    codigo = _codigo_enviado(ambiente)
    errado = "10000" if codigo != "10000" else "10001"

    resposta_errado = _redefinir(ambiente, errado, token)
    resposta_outra = _redefinir(ambiente, codigo, token, email="outra@example.com")

    assert resposta_errado.status_code == resposta_outra.status_code == 400
    assert resposta_errado.json()["detail"] == "Código inválido ou expirado."
    assert _senha_confere(ambiente, _SENHA_ANTIGA)
    assert _senha_confere(ambiente, "Outra-senha-1", "u2")


@pytest.mark.parametrize("email", ["ninguem@example.com", "removida@example.com"])
def test_conta_inexistente_ou_removida_nao_redefine_com_codigo_emitido(ambiente, email):
    emitido = ServicoVerificacaoEmail().emitir(email, "redefinicao", "")

    resposta = _redefinir(ambiente, emitido["codigo"], emitido["token_verificacao"], email)

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Código inválido ou expirado."
    assert ambiente.usuarios[2]["senha_hash"] is None


def test_tentativas_erradas_bloqueiam_ate_o_codigo_correto(ambiente):
    token = _recuperar(ambiente).json()["token_verificacao"]
    codigo = _codigo_enviado(ambiente)
    errado = "10000" if codigo != "10000" else "10001"

    status = [_redefinir(ambiente, errado, token).status_code for _ in range(5)]
    correto = _redefinir(ambiente, codigo, token)

    assert status == [400, 400, 400, 400, 429]
    assert correto.status_code == 429
    assert _senha_confere(ambiente, _SENHA_ANTIGA)


def test_nova_senha_invalida_retorna_422(ambiente):
    token = _recuperar(ambiente).json()["token_verificacao"]
    codigo = _codigo_enviado(ambiente)

    vazia = _redefinir(ambiente, codigo, token, senha="")
    longa = _redefinir(ambiente, codigo, token, senha="a" * 73)
    formato = _redefinir(ambiente, "12a45", token)

    assert vazia.status_code == longa.status_code == formato.status_code == 422
    assert _senha_confere(ambiente, _SENHA_ANTIGA)
