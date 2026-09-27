import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_KEY", "unit-test-placeholder")

from core.autenticacao import obter_usuario_atual  # noqa: E402
from core.database import get_supabase  # noqa: E402
from main import app  # noqa: E402


def test_post_conclusoes_envia_tarefa_e_usuario_ao_servico(monkeypatch):
    usuario_id = uuid4()
    tarefa_id = uuid4()
    casa_id = uuid4()
    inicio = datetime.now(timezone.utc) - timedelta(days=1)
    vencimento = inicio + timedelta(days=2)
    resultado = {
        "id": str(tarefa_id),
        "nome": "Lavar louça",
        "estado_atual": "finalizado",
        "peso": 1,
        "pontuacao": 10,
        "atraso_maximo": 1,
        "referencia_inicio": "criacao",
        "prazo_dias": 2,
        "data_inicio": inicio.isoformat(),
        "proxima_ocorrencia": None,
        "data_fim": vencimento.isoformat(),
        "fk_casa_id": str(casa_id),
        "fk_usuario_id": str(usuario_id),
        "usuarios_atribuidos": [str(usuario_id)],
        "concluida_em": datetime.now(timezone.utc).isoformat(),
        "resultado_pontuacao": {
            "pontos_possiveis": 10,
            "pontos_ganhos": 10,
            "saldo_atual": 10,
        },
    }
    chamadas = []

    class ServicoTarefaFalso:
        def __init__(self, supabase):
            assert supabase is banco

        def concluir_tarefa(self, id_recebido, usuario_recebido):
            chamadas.append((id_recebido, usuario_recebido))
            return resultado

    banco = object()
    monkeypatch.setattr("routers.tarefa.ServicoTarefa", ServicoTarefaFalso)
    app.dependency_overrides[obter_usuario_atual] = lambda: SimpleNamespace(id=usuario_id)
    app.dependency_overrides[get_supabase] = lambda: banco
    try:
        with TestClient(app) as cliente:
            resposta = cliente.post(f"/tarefas/{tarefa_id}/conclusoes")
    finally:
        app.dependency_overrides.pop(obter_usuario_atual, None)
        app.dependency_overrides.pop(get_supabase, None)

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["resultado_pontuacao"]["pontos_ganhos"] == 10
    assert chamadas == [(tarefa_id, usuario_id)]
