import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from test_servico_placar_unitario import evento, montar_servico

load_dotenv()
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_KEY", "unit-test-placeholder")

from core.autenticacao import obter_usuario_atual  # noqa: E402
from core.database import get_supabase  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture
def consulta_score(monkeypatch):
    _, banco, casa_id, usuario_id = montar_servico(score=75)
    monkeypatch.setitem(app.dependency_overrides, get_supabase, lambda: banco)
    monkeypatch.setitem(
        app.dependency_overrides, obter_usuario_atual, lambda: SimpleNamespace(id=usuario_id)
    )
    with TestClient(app) as cliente:
        yield cliente, banco, casa_id, usuario_id


def test_consulta_saldo_por_usuario_e_casa(consulta_score):
    cliente, _, casa_id, usuario_id = consulta_score

    resposta = cliente.get(f"/casas/{casa_id}/saldo", params={"fk_usuario_id": str(usuario_id)})

    assert resposta.status_code == 200, resposta.text
    assert resposta.json() == {
        "fk_casa_id": str(casa_id), "fk_usuario_id": str(usuario_id), "saldo_atual": 75,
    }


def test_extrato_e_ranking_aplicam_periodo_informado_na_url(consulta_score):
    cliente, banco, casa_id, usuario_id = consulta_score
    credito = evento(casa_id, usuario_id, "2026-09-01T03:00:00Z", 50)
    banco.registros["score_event"] = [
        credito,
        evento(casa_id, usuario_id, "2026-10-01T03:00:00Z", 25),
    ]
    periodo = {"data_inicio": "2026-09-01", "data_fim": "2026-10-01"}

    ranking = cliente.get(f"/casas/{casa_id}/ranking", params=periodo)
    extrato = cliente.get(f"/casas/{casa_id}/extrato", params={
        **periodo, "fk_usuario_id": str(usuario_id), "inicio": 0, "limite": 1,
    })

    assert ranking.status_code == extrato.status_code == 200
    assert ranking.json() == {
        "casa_id": str(casa_id), "fuso_horario": "America/Sao_Paulo", **periodo,
        "moradores": [{
            "usuario_id": str(usuario_id), "nome": "Ana", "pontos": 50, "posicao": 1,
        }],
    }
    assert extrato.json() == {
        "casa_id": str(casa_id), "fuso_horario": "America/Sao_Paulo", **periodo,
        "fk_usuario_id": str(usuario_id), "inicio": 0, "limite": 1,
        "total": 1, "eventos": [credito],
    }


@pytest.mark.parametrize("rota", ["saldo", "extrato", "ranking"])
@pytest.mark.parametrize("acesso,status", [
    ("sem_sessao", 401), ("fora_da_casa", 403), ("casa_inexistente", 404),
    ("morador", 200), ("proprietario_sem_vinculo", 200),
])
def test_consultas_exigem_sessao_e_acesso_a_casa(consulta_score, monkeypatch, rota, acesso, status):
    cliente, banco, casa_id, usuario_id = consulta_score
    if acesso == "sem_sessao":
        monkeypatch.delitem(app.dependency_overrides, obter_usuario_atual)
    elif acesso in {"fora_da_casa", "morador", "proprietario_sem_vinculo"}:
        solicitante_id = uuid4()
        monkeypatch.setitem(
            app.dependency_overrides, obter_usuario_atual,
            lambda: SimpleNamespace(id=solicitante_id),
        )
        if acesso == "morador":
            banco.registros["usuario"].append({"id": str(solicitante_id), "nome": "Bia"})
            banco.registros["pertencer"].append({
                "fk_casa_id": str(casa_id), "fk_usuario_id": str(solicitante_id), "score": 0,
            })
        elif acesso == "proprietario_sem_vinculo":
            banco.registros["casa"][0]["fk_usuario_id"] = str(solicitante_id)
    elif acesso == "casa_inexistente":
        casa_id = uuid4()

    params = {"fk_usuario_id": str(usuario_id)} if rota == "saldo" else {}
    resposta = cliente.get(f"/casas/{casa_id}/{rota}", params=params)

    assert resposta.status_code == status, resposta.text


@pytest.mark.parametrize("rota", ["saldo", "extrato"])
def test_consulta_nao_aceita_usuario_vinculado_apenas_a_outra_casa(consulta_score, rota):
    cliente, banco, casa_id, _ = consulta_score
    outro_usuario = uuid4()
    banco.registros["pertencer"].append({
        "fk_casa_id": str(uuid4()), "fk_usuario_id": str(outro_usuario), "score": 999,
    })

    resposta = cliente.get(
        f"/casas/{casa_id}/{rota}", params={"fk_usuario_id": str(outro_usuario)}
    )

    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Vínculo não encontrado."}


@pytest.mark.parametrize("rota", ["extrato", "ranking"])
@pytest.mark.parametrize("params", [
    {"data_inicio": "data-invalida"},
    {"data_fim": "2026-02-30"},
    {"data_inicio": "2026-10-01", "data_fim": "2026-09-01"},
    {"data_inicio": "2026-09-01", "data_fim": "2026-09-01"},
])
def test_periodo_invalido_retorna_422(consulta_score, rota, params):
    cliente, _, casa_id, _ = consulta_score

    resposta = cliente.get(f"/casas/{casa_id}/{rota}", params=params)

    assert resposta.status_code == 422, resposta.text


@pytest.mark.parametrize("params", [
    {"inicio": -1}, {"limite": 0}, {"limite": 101}, {"fk_usuario_id": "invalido"},
])
def test_filtros_invalidos_do_extrato_retornam_422(consulta_score, params):
    cliente, _, casa_id, _ = consulta_score

    resposta = cliente.get(f"/casas/{casa_id}/extrato", params=params)

    assert resposta.status_code == 422, resposta.text


def test_saldo_exige_identificador_do_usuario(consulta_score):
    cliente, _, casa_id, _ = consulta_score

    assert cliente.get(f"/casas/{casa_id}/saldo").status_code == 422
