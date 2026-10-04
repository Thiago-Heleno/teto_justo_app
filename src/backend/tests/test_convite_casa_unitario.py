"""Testes do convite assinado para entrada em uma casa."""

import base64
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

import services.convite_casa as modulo_convite
from services.convite_casa import ServicoConviteCasa


_SEGREDO = "chave-de-testes-com-mais-de-trinta-e-dois-bytes"


def _fixar_relogio(monkeypatch, instante):
    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):
            return instante.astimezone(tz) if tz else instante.replace(tzinfo=None)

    monkeypatch.setattr(modulo_convite, "datetime", Relogio)


def test_emitir_e_verificar_preservam_ids_e_expiracao_utc(monkeypatch):
    monkeypatch.setenv("CASA_CONVITE_SECRET", _SEGREDO)
    agora = datetime(2026, 10, 4, 15, 30, tzinfo=timezone.utc)
    _fixar_relogio(monkeypatch, agora)
    id_casa, id_proprietario = uuid4(), uuid4()
    servico = ServicoConviteCasa()

    resposta = servico.emitir(id_casa, id_proprietario)

    assert resposta["expira_em"] == agora + timedelta(hours=24)
    assert servico.verificar(resposta["convite"]) == (id_casa, id_proprietario)
    assert resposta["convite"].count(".") == 1


def test_convite_com_casa_alterada_sem_nova_assinatura_recebe_400(monkeypatch):
    monkeypatch.setenv("CASA_CONVITE_SECRET", _SEGREDO)
    servico = ServicoConviteCasa()
    convite = servico.emitir(uuid4(), uuid4())["convite"]
    parte_dados, assinatura = convite.split(".")
    dados = json.loads(base64.urlsafe_b64decode(parte_dados + "=="))
    dados["casa_id"] = str(uuid4())
    conteudo_alterado = json.dumps(dados, sort_keys=True, separators=(",", ":")).encode()
    parte_alterada = base64.urlsafe_b64encode(conteudo_alterado).rstrip(b"=").decode()

    with pytest.raises(HTTPException) as erro:
        servico.verificar(f"{parte_alterada}.{assinatura}")

    assert erro.value.status_code == 400
    assert erro.value.detail == "Convite inválido ou expirado."


def test_convite_expirado_recebe_400(monkeypatch):
    monkeypatch.setenv("CASA_CONVITE_SECRET", _SEGREDO)
    agora = datetime(2026, 10, 4, 15, 30, tzinfo=timezone.utc)
    _fixar_relogio(monkeypatch, agora)
    servico = ServicoConviteCasa()
    convite = servico.emitir(uuid4(), uuid4())["convite"]

    _fixar_relogio(monkeypatch, agora + timedelta(hours=24))
    with pytest.raises(HTTPException) as erro:
        servico.verificar(convite)

    assert erro.value.status_code == 400
    assert erro.value.detail == "Convite inválido ou expirado."


def test_rotacao_do_segredo_invalida_convite(monkeypatch):
    monkeypatch.setenv("CASA_CONVITE_SECRET", _SEGREDO)
    servico = ServicoConviteCasa()
    convite = servico.emitir(uuid4(), uuid4())["convite"]
    monkeypatch.setenv("CASA_CONVITE_SECRET", "outro-segredo-longo-com-mais-de-trinta-e-dois-bytes")

    with pytest.raises(HTTPException) as erro:
        servico.verificar(convite)

    assert erro.value.status_code == 400


@pytest.mark.parametrize("segredo", [None, "curto"])
def test_segredo_ausente_ou_curto_desabilita_emissao_e_verificacao(monkeypatch, segredo):
    if segredo is None:
        monkeypatch.delenv("CASA_CONVITE_SECRET", raising=False)
    else:
        monkeypatch.setenv("CASA_CONVITE_SECRET", segredo)
    servico = ServicoConviteCasa()

    for operacao in (
        lambda: servico.emitir(uuid4(), uuid4()),
        lambda: servico.verificar("convite.invalido"),
    ):
        with pytest.raises(HTTPException) as erro:
            operacao()
        assert erro.value.status_code == 503
        assert erro.value.detail == "Serviço de convites indisponível."
