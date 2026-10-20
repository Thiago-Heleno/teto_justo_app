"""Testes unitários do código de verificação de e-mail (sem estado, sem rede)."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

import services.verificacao_email as modulo
from services.verificacao_email import ServicoVerificacaoEmail


_SEGREDO = "chave-de-testes-com-mais-de-trinta-e-dois-bytes"
_EMAIL = "morador@example.com"


@pytest.fixture(autouse=True)
def segredo(monkeypatch):
    monkeypatch.setenv("CASA_CONVITE_SECRET", _SEGREDO)


def _fixar_relogio(monkeypatch, instante):
    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):
            return instante.astimezone(tz) if tz else instante.replace(tzinfo=None)

    monkeypatch.setattr(modulo, "datetime", Relogio)


def test_codigo_tem_cinco_digitos_sem_zero_a_esquerda():
    servico = ServicoVerificacaoEmail()

    codigos = [servico.emitir(_EMAIL)["codigo"] for _ in range(300)]

    assert all(len(c) == 5 and c.isdigit() and c[0] != "0" for c in codigos)
    assert len(set(codigos)) > 1


def test_codigo_emitido_e_aceito_ignorando_caixa_e_espacos_do_email():
    servico = ServicoVerificacaoEmail()
    emitido = servico.emitir(" Morador@Example.com ")

    servico.verificar(_EMAIL, emitido["codigo"], emitido["token_verificacao"])


def test_expiracao_e_de_dez_minutos(monkeypatch):
    agora = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
    _fixar_relogio(monkeypatch, agora)
    servico = ServicoVerificacaoEmail()

    emitido = servico.emitir(_EMAIL)
    assert emitido["expira_em"] == agora + timedelta(minutes=10)

    _fixar_relogio(monkeypatch, agora + timedelta(minutes=9, seconds=59))
    servico.verificar(_EMAIL, emitido["codigo"], emitido["token_verificacao"])

    _fixar_relogio(monkeypatch, agora + timedelta(minutes=10))
    with pytest.raises(HTTPException) as erro:
        servico.verificar(_EMAIL, emitido["codigo"], emitido["token_verificacao"])
    assert erro.value.status_code == 400


def test_rejeita_codigo_errado_email_diferente_e_token_adulterado():
    servico = ServicoVerificacaoEmail()
    emitido = servico.emitir(_EMAIL)
    errado = "10000" if emitido["codigo"] != "10000" else "10001"
    exp, assinatura = emitido["token_verificacao"].split(".")
    tokens_invalidos = [
        emitido["token_verificacao"],
        f"{int(exp) + 60}.{assinatura}",
        f"{exp}.{assinatura[:-1]}0" if assinatura[-1] != "0" else f"{exp}.{assinatura[:-1]}1",
    ]

    for email, codigo, token in [
        (_EMAIL, errado, emitido["token_verificacao"]),
        ("outro@example.com", emitido["codigo"], emitido["token_verificacao"]),
        (_EMAIL, emitido["codigo"], tokens_invalidos[1]),
        (_EMAIL, emitido["codigo"], tokens_invalidos[2]),
    ]:
        with pytest.raises(HTTPException) as erro:
            servico.verificar(email, codigo, token)
        assert erro.value.status_code == 400
        assert erro.value.detail == "Código inválido ou expirado."


def test_codigo_so_vale_para_o_proposito_e_o_vinculo_com_que_foi_emitido():
    servico = ServicoVerificacaoEmail()
    emitido = servico.emitir(_EMAIL, "redefinicao", "hash-1")
    codigo, token = emitido["codigo"], emitido["token_verificacao"]

    servico.verificar(_EMAIL, codigo, token, "redefinicao", "hash-1")
    outros = [("cadastro", "hash-1"), ("redefinicao", "hash-2"), ("redefinicao", "")]
    for proposito, vinculo in outros:
        with pytest.raises(HTTPException) as erro:
            servico.verificar(_EMAIL, codigo, token, proposito, vinculo)
        assert erro.value.status_code == 400


@pytest.mark.parametrize("token", ["", "sem-ponto", "abc.def", "1.2.3", "9999999999.é"])
def test_token_malformado_retorna_400_sem_erro_interno(token):
    with pytest.raises(HTTPException) as erro:
        ServicoVerificacaoEmail().verificar(_EMAIL, "12345", token)

    assert erro.value.status_code == 400


def test_sem_segredo_configurado_retorna_503(monkeypatch):
    monkeypatch.setenv("CASA_CONVITE_SECRET", "curto")

    with pytest.raises(HTTPException) as erro:
        ServicoVerificacaoEmail().emitir(_EMAIL)

    assert erro.value.status_code == 503


def test_html_traz_o_codigo_e_as_cores_do_design_system():
    html = ServicoVerificacaoEmail.montar_html("48213")

    assert ">48213</p>" in html
    for cor in ("#e2e2df", "#f7f6f2", "#fc5000", "#f5f28e", "#070607"):
        assert cor in html


def test_html_aceita_titulo_e_texto_proprios():
    html = ServicoVerificacaoEmail.montar_html(
        "48213", "Redefina sua senha", "Crie uma nova senha."
    )

    assert "Redefina sua senha" in html
    assert "Crie uma nova senha." in html
    assert "Confirme seu e-mail" not in html
