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


def test_ocorrencia_so_pode_ser_criada_pelo_worker(payload):
    with pytest.raises(ValidationError):
        TarefaCriar(**payload, referencia_inicio="ocorrencia")


def test_datas_internas_da_ocorrencia_nao_sao_aceitas_na_criacao(payload):
    inicio = datetime.now(timezone.utc) + timedelta(days=1)
    for campo in ["data_inicio", "proxima_ocorrencia"]:
        with pytest.raises(ValidationError):
            TarefaCriar(**payload, **{campo: inicio})


def test_dia_fixo_exige_data_e_intervalo_a_proibe(payload):
    with pytest.raises(ValidationError):
        TarefaCriar(**payload, modo_prazo="dia_fixo")
    with pytest.raises(ValidationError):
        TarefaCriar(**payload, data_fixa="2030-01-01")
    assert TarefaCriar(**payload, modo_prazo="dia_fixo", data_fixa="2030-01-01").data_fixa


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("tipo", "rotativa"),
        ("tipo", "outra"),
        ("modo_prazo", "semanal"),
    ],
)
def test_http_rejeita_tipo_ou_modo_nao_suportado(cliente, payload, campo, valor):
    resposta = cliente.post("/tarefas/", json={**payload, campo: valor})
    assert resposta.status_code == 422
    assert any(erro["loc"][-1] == campo for erro in resposta.json()["detail"])


@pytest.mark.parametrize("campo,valor", [("tipo", "rotativa"), ("modo_prazo", "dia_fixo")])
def test_http_nao_permite_alterar_tipo_ou_modo(cliente, campo, valor):
    resposta = cliente.patch("/tarefas/id", json={campo: valor})
    assert resposta.status_code == 422
    assert any(erro["loc"][-1] == campo for erro in resposta.json()["detail"])


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
