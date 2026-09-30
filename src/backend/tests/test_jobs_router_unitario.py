from fastapi.testclient import TestClient

from core.database import get_supabase
from main import app


def test_endpoint_job_exige_token_configurado(monkeypatch):
    monkeypatch.delenv("PENALIDADE_JOB_TOKEN", raising=False)
    banco = object()
    app.dependency_overrides[get_supabase] = lambda: banco

    try:
        with TestClient(app) as cliente:
            resposta = cliente.post("/jobs/penalidades")
    finally:
        app.dependency_overrides.pop(get_supabase, None)

    assert resposta.status_code == 503


def test_endpoint_job_rejeita_token_incorreto(monkeypatch):
    monkeypatch.setenv("PENALIDADE_JOB_TOKEN", "token-de-teste")
    banco = object()
    app.dependency_overrides[get_supabase] = lambda: banco

    try:
        with TestClient(app) as cliente:
            resposta = cliente.post(
                "/jobs/penalidades",
                headers={"X-Penalidade-Job-Token": "token-incorreto"},
            )
    finally:
        app.dependency_overrides.pop(get_supabase, None)

    assert resposta.status_code == 401


def test_endpoint_job_invoca_servico_com_token_valido(monkeypatch):
    monkeypatch.setenv("PENALIDADE_JOB_TOKEN", "token-de-teste")
    banco = object()
    resultado = {
        "tarefas_analisadas": 4,
        "marcadas_atrasadas": 2,
        "marcadas_nao_feitas": 1,
    }
    chamadas = []

    class ServicoFalso:
        def __init__(self, supabase):
            assert supabase is banco

        def processar_tarefas(self):
            chamadas.append(True)
            return resultado

    monkeypatch.setattr("routers.jobs.ServicoPenalidade", ServicoFalso)
    app.dependency_overrides[get_supabase] = lambda: banco
    try:
        with TestClient(app) as cliente:
            resposta = cliente.post(
                "/jobs/penalidades",
                headers={"X-Penalidade-Job-Token": "token-de-teste"},
            )
    finally:
        app.dependency_overrides.pop(get_supabase, None)

    assert resposta.status_code == 200
    assert resposta.json() == resultado
    assert chamadas == [True]
