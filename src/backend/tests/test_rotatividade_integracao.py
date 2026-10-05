"""Integração do agendamento automático de rodízios com o Supabase de teste."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from core.database import get_supabase
from main import app


@pytest.fixture
def ambiente_rotatividade(
    autenticacao_temporaria,
    criar_autenticacao_temporaria,
):
    supabase = get_supabase()
    configuracoes_ativas = (
        supabase.table("rotatividade")
        .select("id")
        .eq("ativa", True)
        .limit(1)
        .execute()
        .data
    )
    assert not configuracoes_ativas, (
        "Este teste processa todos os rodízios ativos. "
        "Use um Supabase de teste sem rodízios ativos."
    )

    marcador = uuid4().hex
    proprietario_id = autenticacao_temporaria["usuario_id"]
    participante = criar_autenticacao_temporaria()
    casa_id = None

    try:
        resposta_casa = (
            supabase.table("casa")
            .insert(
                {
                    "nome": f"Casa teste rotatividade {marcador}",
                    "fk_usuario_id": proprietario_id,
                    "timezone": "UTC",
                }
            )
            .execute()
        )
        assert resposta_casa.data, "Não foi possível criar a casa de teste."
        casa_id = resposta_casa.data[0]["id"]

        resposta_vinculos = (
            supabase.table("pertencer")
            .insert(
                [
                    {
                        "fk_usuario_id": proprietario_id,
                        "fk_casa_id": casa_id,
                        "score": 0,
                    },
                    {
                        "fk_usuario_id": participante["usuario_id"],
                        "fk_casa_id": casa_id,
                        "score": 0,
                    },
                ]
            )
            .execute()
        )
        assert len(resposta_vinculos.data or []) == 2, (
            "Não foi possível vincular os participantes à casa de teste."
        )

        yield {
            "casa_id": casa_id,
            "proprietario_id": proprietario_id,
            "participante_id": participante["usuario_id"],
        }
    finally:
        if casa_id is not None:
            configuracoes = (
                supabase.table("rotatividade")
                .select("id")
                .eq("fk_casa_id", casa_id)
                .execute()
                .data
            )
            for configuracao in configuracoes:
                tarefas = (
                    supabase.table("tarefa")
                    .select("id")
                    .eq("rotatividade_id", configuracao["id"])
                    .execute()
                    .data
                )
                ids_tarefas = [tarefa["id"] for tarefa in tarefas]
                if ids_tarefas:
                    supabase.table("score_event").delete().in_(
                        "fk_tarefa_id", ids_tarefas
                    ).execute()
                    supabase.table("atribuida").delete().in_(
                        "fk_tarefa_id", ids_tarefas
                    ).execute()
                    supabase.table("tarefa").delete().in_(
                        "id", ids_tarefas
                    ).execute()
                (
                    supabase.table("rotatividade_participante")
                    .delete()
                    .eq("fk_rotatividade_id", configuracao["id"])
                    .execute()
                )
                (
                    supabase.table("rotatividade")
                    .delete()
                    .eq("id", configuracao["id"])
                    .execute()
                )
            supabase.table("pertencer").delete().eq(
                "fk_casa_id", casa_id
            ).execute()
            supabase.table("casa").delete().eq("id", casa_id).execute()


def test_criar_e_processar_rotatividade_no_supabase(
    ambiente_rotatividade,
    autenticacao_temporaria,
    monkeypatch,
):
    supabase = get_supabase()
    proprietario_id = ambiente_rotatividade["proprietario_id"]
    participante_id = ambiente_rotatividade["participante_id"]
    token_job = uuid4().hex
    monkeypatch.setenv("ROTATIVIDADE_JOB_TOKEN", token_job)

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente:
        criada = cliente.post(
            "/rotatividades/",
            json={
                "fk_casa_id": ambiente_rotatividade["casa_id"],
                "nome": "Limpar cozinha - teste de integração",
                "peso": 2,
                "prazo_dias": 2,
                "atraso_maximo": 2,
                "participantes": [proprietario_id, participante_id],
                "dias_semana": [
                    datetime.now(timezone.utc).isoweekday()
                ],
                "intervalo_semanas": 1,
            },
        )
        assert criada.status_code == 201, criada.text
        rotatividade = criada.json()

        participantes = (
            supabase.table("rotatividade_participante")
            .select("fk_usuario_id,ordem")
            .eq("fk_rotatividade_id", rotatividade["id"])
            .order("ordem")
            .execute()
            .data
        )
        assert [item["fk_usuario_id"] for item in participantes] == [
            proprietario_id,
            participante_id,
        ]

        # A criação já gera a ocorrência de hoje; o job só repara o que faltar.
        tarefas_apos_criar = (
            supabase.table("tarefa")
            .select("id")
            .eq("rotatividade_id", rotatividade["id"])
            .execute()
            .data
        )
        assert len(tarefas_apos_criar) == 1

        processamento = cliente.post(
            "/jobs/rotatividades",
            headers={"X-Rotatividade-Job-Token": token_job},
        )
        assert processamento.status_code == 200, processamento.text
        assert processamento.json() == {
            "rotatividades_analisadas": 1,
            "ocorrencias_processadas": 0,
        }

    tarefas = (
        supabase.table("tarefa")
        .select(
            "id,tipo,pontuacao,fk_casa_id,rotatividade_id,ocorrencia_em,timezone"
        )
        .eq("rotatividade_id", rotatividade["id"])
        .execute()
        .data
    )
    assert len(tarefas) == 1
    tarefa = tarefas[0]
    assert tarefa["tipo"] == "rotativa"
    assert tarefa["pontuacao"] == 25
    assert tarefa["fk_casa_id"] == ambiente_rotatividade["casa_id"]
    assert tarefa["ocorrencia_em"] is not None
    assert tarefa["timezone"] == "UTC"

    atribuicoes = (
        supabase.table("atribuida")
        .select("fk_usuario_id")
        .eq("fk_tarefa_id", tarefa["id"])
        .execute()
        .data
    )
    assert len(atribuicoes) == 1
    assert atribuicoes[0]["fk_usuario_id"] in {
        proprietario_id,
        participante_id,
    }
