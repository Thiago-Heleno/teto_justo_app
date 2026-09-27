"""Verifica rodízio com as RPCs e constraints em um Supabase de testes migrado."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timezone
from threading import Barrier
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from core.database import get_supabase
from main import app
from services.rotatividade import ServicoRotatividade


def _primeira_segunda_do_mes_seguinte() -> date:
    agora = datetime.now(ZoneInfo("America/Sao_Paulo"))
    if agora.month == 12:
        primeiro = date(agora.year + 1, 1, 1)
    else:
        primeiro = date(agora.year, agora.month + 1, 1)
    return primeiro.replace(day=1 + (7 - primeiro.weekday()) % 7)


def test_ocorrencias_reais_equilibram_potencial_e_nao_duplicam(
    autenticacao_temporaria, criar_autenticacao_temporaria
):
    banco = get_supabase()
    administrador = autenticacao_temporaria["usuario_id"]
    outro = criar_autenticacao_temporaria()["usuario_id"]
    casa = banco.table("casa").insert({
        "nome": f"Casa rodízio {uuid4().hex}",
        "fk_usuario_id": administrador,
        "timezone": "America/Sao_Paulo",
    }).execute().data[0]["id"]
    rotatividade_id = None
    try:
        banco.table("pertencer").insert([
            {"fk_casa_id": casa, "fk_usuario_id": administrador, "score": 0},
            {"fk_casa_id": casa, "fk_usuario_id": outro, "score": 0},
        ]).execute()
        segunda = _primeira_segunda_do_mes_seguinte()
        config = {
            "fk_casa_id": casa,
            "fk_usuario_id": administrador,
            "nome": "Limpar cozinha",
            "descricao": None,
            "dificuldade": 2,
            "pontuacao": 25,
            "prazo_dias": 2,
            "atraso_maximo": 5,
            "modo_prazo": "dia_fixo",
            "timezone_esperado": "America/Sao_Paulo",
            "dias_semana": [1, 3],
            "intervalo_semanas": 1,
            "semana_ancora": segunda.isoformat(),
        }
        rotatividade = banco.rpc("criar_rotatividade", {
            "p_config": config,
            "p_participantes": [administrador, outro],
        }).execute().data
        rotatividade_id = rotatividade["id"]

        quarta = segunda.replace(day=segunda.day + 2)
        agora = datetime.combine(
            quarta, time(hour=12), tzinfo=ZoneInfo("America/Sao_Paulo")
        ).astimezone(timezone.utc)
        barreira = Barrier(2, timeout=10)

        def processar():
            barreira.wait()
            return ServicoRotatividade(banco).processar_pendentes(
                agora, rotatividade_id
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futuros = [executor.submit(processar) for _ in range(2)]
            for futuro in futuros:
                futuro.result(timeout=30)
        ServicoRotatividade(banco).processar_pendentes(agora, rotatividade_id)

        tarefas = (
            banco.table("tarefa")
            .select("id,ocorrencia_em,pontuacao")
            .eq("rotatividade_id", rotatividade_id)
            .execute()
        ).data
        assert len(tarefas) == 2
        assert {tarefa["pontuacao"] for tarefa in tarefas} == {25}
        atribuicoes = (
            banco.table("atribuida")
            .select("fk_tarefa_id,fk_usuario_id")
            .in_("fk_tarefa_id", [tarefa["id"] for tarefa in tarefas])
            .execute()
        ).data
        assert {item["fk_usuario_id"] for item in atribuicoes} == {administrador, outro}
        with TestClient(app, headers=autenticacao_temporaria["headers"]) as cliente:
            resposta = cliente.get(f"/rotatividades/{rotatividade_id}/ocorrencias")
            assert resposta.status_code == 200, resposta.text
            assert len(resposta.json()) == 2
            assert {item["tipo"] for item in resposta.json()} == {"rotativa"}
            assert cliente.delete(f"/tarefas/{tarefas[0]['id']}").status_code == 409
    finally:
        if rotatividade_id:
            tarefas = (
                banco.table("tarefa")
                .select("id")
                .eq("rotatividade_id", rotatividade_id)
                .execute()
            ).data
            ids = [tarefa["id"] for tarefa in tarefas]
            if ids:
                banco.table("atribuida").delete().in_("fk_tarefa_id", ids).execute()
                banco.table("tarefa").delete().in_("id", ids).execute()
            banco.table("rotatividade_participante").delete().eq(
                "fk_rotatividade_id", rotatividade_id
            ).execute()
            banco.table("rotatividade").delete().eq("id", rotatividade_id).execute()
        banco.table("pertencer").delete().eq("fk_casa_id", casa).execute()
        banco.table("casa").delete().eq("id", casa).execute()
