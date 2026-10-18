"""Testes unitários do envio de email; o Resend é simulado, sem rede."""

import httpx
import pytest
from fastapi import HTTPException

import services.envio_email as modulo_email
from services.envio_email import ServicoEmail


_CHAVE = "re_chave_falsa_de_testes"


@pytest.fixture
def requisicoes(monkeypatch):
    chamadas = []

    def post_falso(url, **kwargs):
        chamadas.append((url, kwargs))
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(modulo_email.httpx, "post", post_falso)
    monkeypatch.delenv("RESEND_FROM", raising=False)
    return chamadas


def test_sem_chave_levanta_503_e_nao_faz_requisicao(monkeypatch, requisicoes):
    monkeypatch.delenv("RESEND_API", raising=False)

    with pytest.raises(HTTPException) as erro:
        ServicoEmail().enviar("a@example.com", "Assunto", "<p>oi</p>")

    assert erro.value.status_code == 503
    assert requisicoes == []


def test_envia_payload_com_remetente_padrao(monkeypatch, requisicoes):
    monkeypatch.setenv("RESEND_API", _CHAVE)

    ServicoEmail().enviar("a@example.com", "Assunto", "<p>oi</p>")

    (url, kwargs), = requisicoes
    assert url == "https://api.resend.com/emails"
    assert kwargs["headers"] == {"Authorization": f"Bearer {_CHAVE}"}
    assert kwargs["json"] == {
        "from": "onboarding@resend.dev",
        "to": "a@example.com",
        "subject": "Assunto",
        "html": "<p>oi</p>",
    }


def test_usa_remetente_configurado(monkeypatch, requisicoes):
    monkeypatch.setenv("RESEND_API", _CHAVE)
    monkeypatch.setenv("RESEND_FROM", "Teto Justo <nao-responda@example.com>")

    ServicoEmail().enviar(["a@example.com", "b@example.com"], "Assunto", "<p>oi</p>")

    payload = requisicoes[0][1]["json"]
    assert payload["from"] == "Teto Justo <nao-responda@example.com>"
    assert payload["to"] == ["a@example.com", "b@example.com"]


@pytest.mark.parametrize(
    "falha",
    [
        httpx.Response(401, request=httpx.Request("POST", "https://api.resend.com/emails")),
        httpx.Response(500, request=httpx.Request("POST", "https://api.resend.com/emails")),
        httpx.ReadTimeout("tempo esgotado"),
        httpx.ConnectError("sem rede"),
    ],
    ids=["401", "500", "timeout", "rede"],
)
def test_falhas_do_resend_viram_503_sem_vazar_a_chave(monkeypatch, falha):
    monkeypatch.setenv("RESEND_API", _CHAVE)

    def post_falso(url, **kwargs):
        if isinstance(falha, Exception):
            raise falha
        return falha

    monkeypatch.setattr(modulo_email.httpx, "post", post_falso)

    with pytest.raises(HTTPException) as erro:
        ServicoEmail().enviar("a@example.com", "Assunto", "<p>oi</p>")

    assert erro.value.status_code == 503
    assert _CHAVE not in erro.value.detail
