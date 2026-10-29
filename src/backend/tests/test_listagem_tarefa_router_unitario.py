from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.autenticacao import obter_usuario_atual
from core.database import get_supabase
from routers.tarefa import router


@pytest.mark.parametrize("estado,status", [("em_aberto", 200), ("invalido", 422)])
def test_lista_valida_filtro_de_estado_e_preserva_autorizacao(monkeypatch, estado, status):
    app = FastAPI()
    app.include_router(router)
    casa_id, usuario_id, responsavel = uuid4(), uuid4(), uuid4()
    banco = object()
    app.dependency_overrides[get_supabase] = lambda: banco
    app.dependency_overrides[obter_usuario_atual] = lambda: SimpleNamespace(id=usuario_id)
    servico = MagicMock()
    servico.listar_tarefas_por_casa.return_value = []
    autorizar = MagicMock()
    monkeypatch.setattr("routers.tarefa.ServicoTarefa", MagicMock(return_value=servico))
    monkeypatch.setattr("routers.tarefa.ServicoAutorizacaoCasa.garantir_acesso", autorizar)

    with TestClient(app) as cliente:
        resposta = cliente.get(
            f"/tarefas/casa/{casa_id}",
            params={"estado": estado, "responsavel": str(responsavel), "prazo": "sete_dias"},
        )

    assert resposta.status_code == status, resposta.text
    if status == 200:
        assert resposta.json() == []
        autorizar.assert_called_once_with(casa_id, usuario_id)
        servico.listar_tarefas_por_casa.assert_called_once_with(
            casa_id, estado="em_aberto", responsavel=responsavel, prazo="sete_dias"
        )
    else:
        servico.listar_tarefas_por_casa.assert_not_called()
