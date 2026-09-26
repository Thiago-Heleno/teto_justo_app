"""Contrato HTTP dos schemas, sem conexão com banco de dados."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from schemas.tarefa import TarefaAtualizar, TarefaCriar


@pytest.fixture
def payload():
    return {
        "nome": "Lavar louça",
        "peso": 3,
        "prazo_dias": 3,
        "atraso_maximo": 1,
        "fk_casa_id": str(uuid4()),
        "usuarios_atribuidos": [str(uuid4())],
    }


@pytest.fixture
def cliente():
    app = FastAPI()

    @app.post("/tarefas/")
    def criar(tarefa: TarefaCriar):
        return tarefa

    @app.patch("/tarefas/{id_tarefa}")
    def atualizar(id_tarefa: str, tarefa: TarefaAtualizar):
        return tarefa

    with TestClient(app) as cliente:
        yield cliente


@pytest.mark.parametrize("pontos", [10, 25, 50, 999, None])
def test_http_rejeita_pontuacao_enviada_pelo_cliente(cliente, payload, pontos):
    for method, url, dados in [
        (cliente.post, "/tarefas/", {**payload, "pontuacao": pontos}),
        (cliente.patch, "/tarefas/qualquer-id", {"pontuacao": pontos}),
    ]:
        resposta = method(url, json=dados)
        assert resposta.status_code == 422
        assert any(e["loc"][-1] == "pontuacao" for e in resposta.json()["detail"])


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("peso", 4),
        ("peso", True),
        ("peso", "2"),
        ("prazo_dias", 0),
        ("prazo_dias", 6),
        ("prazo_dias", 1.5),
        ("prazo_dias", True),
        ("atraso_maximo", 0),
        ("atraso_maximo", 1.5),
        ("atraso_maximo", True),
        ("nome", "   "),
        ("usuarios_atribuidos", []),
        ("usuarios_atribuidos", [str(uuid4()), str(uuid4())]),
    ],
)
def test_rejeita_dados_invalidos_na_criacao_e_edicao(cliente, payload, campo, valor):
    assert cliente.post("/tarefas/", json={**payload, campo: valor}).status_code == 422
    assert cliente.patch("/tarefas/id", json={campo: valor}).status_code == 422


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("fk_usuario_id", str(uuid4())),
        ("data_fim", "2030-01-01T00:00:00Z"),
        ("estado_atual", "finalizado"),
        ("estrategia_penalidade", "livre"),
        ("data_inicio", "2030-01-01T00:00:00Z"),
    ],
)
def test_cliente_nao_define_autor_vencimento_ou_credito_inicial(cliente, payload, campo, valor):
    assert cliente.post("/tarefas/", json={**payload, campo: valor}).status_code == 422


def test_ocorrencia_exige_inicio_e_proxima_ocorrencia(payload):
    with pytest.raises(ValidationError):
        TarefaCriar(**payload, referencia_inicio="ocorrencia")


@pytest.mark.parametrize("dias_proxima,aceita", [(3, False), (4, False), (5, True), (7, True)])
def test_prazo_e_tolerancia_terminam_antes_da_proxima_ocorrencia(payload, dias_proxima, aceita):
    inicio = datetime.now(timezone.utc) + timedelta(days=1)
    dados = {
        **payload,
        "referencia_inicio": "ocorrencia",
        "data_inicio": inicio,
        "proxima_ocorrencia": inicio + timedelta(days=dias_proxima),
    }
    if aceita:
        assert TarefaCriar(**dados).data_inicio == inicio
    else:
        with pytest.raises(ValidationError):
            TarefaCriar(**dados)


def test_ocorrencia_rejeita_datas_sem_fuso_e_inicio_passado(payload):
    inicio = datetime.now(timezone.utc) - timedelta(days=1)
    for data_inicio in [inicio, inicio.replace(tzinfo=None)]:
        with pytest.raises(ValidationError):
            TarefaCriar(
                **payload,
                referencia_inicio="ocorrencia",
                data_inicio=data_inicio,
                proxima_ocorrencia=inicio + timedelta(days=7),
            )


def test_atualizacao_nao_pode_reiniciar_prazo_ou_apagar_regras(cliente):
    for dados in [
        {"data_inicio": "2030-01-01T00:00:00Z"},
        {"referencia_inicio": "criacao"},
        {"peso": None},
        {"prazo_dias": None},
        {"atraso_maximo": None},
        {"usuarios_atribuidos": None},
    ]:
        assert cliente.patch("/tarefas/id", json=dados).status_code == 422
