from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
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


@pytest.fixture(params=["penalidades", "rotatividades", "notificacoes"])
def job_cron(request, monkeypatch):
    nome_servico, metodo, resultado = {
        "penalidades": (
            "ServicoPenalidade",
            "processar_tarefas",
            {"tarefas_analisadas": 4, "marcadas_atrasadas": 2, "marcadas_nao_feitas": 1},
        ),
        "rotatividades": (
            "ServicoAgendamentoRotatividade",
            "processar_ocorrencias",
            {"rotatividades_analisadas": 2, "ocorrencias_processadas": 3},
        ),
        "notificacoes": (
            "ServicoNotificacao",
            "avisar_vencimentos",
            {"tarefas_elegiveis": 2, "avisos_enviados": 1, "falhas": 0},
        ),
    }[request.param]
    banco = object()
    acessos_banco = []

    def obter_banco():
        acessos_banco.append(True)
        return banco

    classe_servico = MagicMock()
    processamento = getattr(classe_servico.return_value, metodo)
    processamento.return_value = resultado
    monkeypatch.setattr(f"routers.jobs.{nome_servico}", classe_servico)
    monkeypatch.delenv("CRON_SECRET", raising=False)
    app.dependency_overrides[get_supabase] = obter_banco
    try:
        with TestClient(app) as cliente:
            yield SimpleNamespace(
                cliente=cliente,
                caminho=f"/jobs/{request.param}",
                banco=banco,
                acessos_banco=acessos_banco,
                classe_servico=classe_servico,
                processamento=processamento,
                resultado=resultado,
            )
    finally:
        app.dependency_overrides.pop(get_supabase, None)


@pytest.mark.parametrize("segredo", [None, ""])
def test_cron_sem_segredo_nao_acessa_banco(job_cron, monkeypatch, segredo):
    if segredo is not None:
        monkeypatch.setenv("CRON_SECRET", segredo)

    resposta = job_cron.cliente.get(job_cron.caminho)

    assert resposta.status_code == 503
    assert job_cron.acessos_banco == []
    job_cron.classe_servico.assert_not_called()


@pytest.mark.parametrize("authorization", [None, "Bearer incorreto", "Basic incorreto", "Bearer"])
def test_cron_rejeita_autenticacao_invalida_antes_do_banco(job_cron, monkeypatch, authorization):
    monkeypatch.setenv("CRON_SECRET", uuid4().hex)
    headers = {} if authorization is None else {"Authorization": authorization}

    resposta = job_cron.cliente.get(job_cron.caminho, headers=headers)

    assert resposta.status_code == 401
    assert job_cron.acessos_banco == []
    job_cron.classe_servico.assert_not_called()


def test_cron_nao_aceita_token_post_nem_user_agent_como_autenticacao(job_cron, monkeypatch):
    segredo = uuid4().hex
    monkeypatch.setenv("CRON_SECRET", segredo)
    monkeypatch.setenv("PENALIDADE_JOB_TOKEN", segredo)
    monkeypatch.setenv("ROTATIVIDADE_JOB_TOKEN", segredo)

    resposta = job_cron.cliente.get(
        job_cron.caminho,
        headers={
            "X-Penalidade-Job-Token": segredo,
            "X-Rotatividade-Job-Token": segredo,
            "User-Agent": "vercel-cron/1.0",
        },
    )

    assert resposta.status_code == 401
    assert job_cron.acessos_banco == []
    job_cron.classe_servico.assert_not_called()


def test_cron_autenticado_executa_servico_sem_cache(job_cron, monkeypatch):
    segredo = uuid4().hex
    monkeypatch.setenv("CRON_SECRET", segredo)
    monkeypatch.delenv("PENALIDADE_JOB_TOKEN", raising=False)
    monkeypatch.delenv("ROTATIVIDADE_JOB_TOKEN", raising=False)

    resposta = job_cron.cliente.get(
        job_cron.caminho,
        headers={"Authorization": f"Bearer {segredo}"},
    )

    assert resposta.status_code == 200
    assert resposta.json() == job_cron.resultado
    assert resposta.headers["Cache-Control"] == "no-store"
    assert job_cron.acessos_banco == [True]
    job_cron.classe_servico.assert_called_once_with(job_cron.banco)
    job_cron.processamento.assert_called_once_with()


def test_endpoint_job_rotatividades_exige_token_configurado(monkeypatch):
    monkeypatch.delenv("ROTATIVIDADE_JOB_TOKEN", raising=False)
    app.dependency_overrides[get_supabase] = lambda: object()
    try:
        with TestClient(app) as cliente:
            resposta = cliente.post("/jobs/rotatividades")
    finally:
        app.dependency_overrides.pop(get_supabase, None)

    assert resposta.status_code == 503


def test_endpoint_job_rotatividades_invoca_servico_com_token_valido(monkeypatch):
    monkeypatch.setenv("ROTATIVIDADE_JOB_TOKEN", "token-de-teste")
    banco = object()
    resultado = {
        "rotatividades_analisadas": 2,
        "ocorrencias_processadas": 3,
    }
    chamadas = []

    class ServicoFalso:
        def __init__(self, supabase):
            assert supabase is banco

        def processar_ocorrencias(self):
            chamadas.append(True)
            return resultado

    monkeypatch.setattr(
        "routers.jobs.ServicoAgendamentoRotatividade",
        ServicoFalso,
    )
    app.dependency_overrides[get_supabase] = lambda: banco
    try:
        with TestClient(app) as cliente:
            resposta = cliente.post(
                "/jobs/rotatividades",
                headers={"X-Rotatividade-Job-Token": "token-de-teste"},
            )
    finally:
        app.dependency_overrides.pop(get_supabase, None)

    assert resposta.status_code == 200
    assert resposta.json() == resultado
    assert chamadas == [True]
