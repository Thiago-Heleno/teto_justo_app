"""Integração de rodízios restrita aos registros criados pelo próprio teste."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from core.database import get_supabase
from main import app
from services.ciclo_vida_tarefa import instante_utc
from services.roleta_rotatividade import ServicoRoletaRotatividade
from services.rotatividade_agendamento import ServicoAgendamentoRotatividade


@pytest.fixture
def ambiente_rotatividade(
    autenticacao_temporaria,
    criar_autenticacao_temporaria,
):
    supabase = get_supabase()
    marcador = uuid4().hex
    administrador_id = autenticacao_temporaria["usuario_id"]
    participante = criar_autenticacao_temporaria()
    casa_id = None

    try:
        resposta_casa = (
            supabase.table("casa")
            .insert(
                {
                    "nome": f"Casa teste rotatividade {marcador}",
                    "fk_usuario_id": administrador_id,
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
                        "fk_usuario_id": administrador_id,
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
            "administrador_id": administrador_id,
            "participante_id": participante["usuario_id"],
            "participante_headers": participante["headers"],
        }
    finally:
        if casa_id is not None:
            configuracoes = (
                supabase.table("rotatividade").select("id").eq("fk_casa_id", casa_id).execute().data
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
                    supabase.table("atribuida").delete().in_("fk_tarefa_id", ids_tarefas).execute()
                    supabase.table("tarefa").delete().in_("id", ids_tarefas).execute()
                (
                    supabase.table("rotatividade_participante")
                    .delete()
                    .eq("fk_rotatividade_id", configuracao["id"])
                    .execute()
                )
                (supabase.table("rotatividade").delete().eq("id", configuracao["id"]).execute())
            supabase.table("pertencer").delete().eq("fk_casa_id", casa_id).execute()
            supabase.table("casa").delete().eq("id", casa_id).execute()


def test_criar_e_processar_rotatividade_no_supabase(
    ambiente_rotatividade,
    autenticacao_temporaria,
    monkeypatch,
):
    supabase = get_supabase()
    administrador_id = ambiente_rotatividade["administrador_id"]
    participante_id = ambiente_rotatividade["participante_id"]
    instante = datetime.now(timezone.utc)

    class RelogioFixo(datetime):
        @classmethod
        def now(cls, tz=None):
            return instante.astimezone(tz) if tz else instante.replace(tzinfo=None)

    monkeypatch.setattr("services.rotatividade_agendamento.datetime", RelogioFixo)

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
                "participantes": [administrador_id, participante_id],
                "dias_semana": [instante.isoweekday()],
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
            administrador_id,
            participante_id,
        ]

        tarefas_apos_criar = (
            supabase.table("tarefa")
            .select("id")
            .eq("rotatividade_id", rotatividade["id"])
            .execute()
            .data
        )
        # Hoje e as 8 semanas seguintes: a janela de 60 dias comporta 9 ocorrências.
        assert len(tarefas_apos_criar) == 9

        configuracao = (
            supabase.table("rotatividade")
            .select("*")
            .eq("id", rotatividade["id"])
            .execute()
            .data[0]
        )
        # O job global também processaria rodízios reais fora deste teste.
        servico = ServicoAgendamentoRotatividade(supabase)
        assert servico._processar_configuracao(configuracao, instante) == 0

    tarefas = (
        supabase.table("tarefa")
        .select("id,tipo,pontuacao,fk_casa_id,rotatividade_id,ocorrencia_em,timezone")
        .eq("rotatividade_id", rotatividade["id"])
        .execute()
        .data
    )
    assert len(tarefas) == 9
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
        administrador_id,
        participante_id,
    }


@pytest.fixture
def cenario_roleta(ambiente_rotatividade, autenticacao_temporaria, monkeypatch):
    supabase = get_supabase()
    ambiente = ambiente_rotatividade
    relogio = [datetime(2033, 8, 22, 18, tzinfo=timezone.utc)]

    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):
            return relogio[0].astimezone(tz) if tz else relogio[0].replace(tzinfo=None)

    monkeypatch.setattr("services.rotatividade_agendamento.datetime", Relogio)
    monkeypatch.setattr("services.roleta_rotatividade.datetime", Relogio)
    monkeypatch.setattr("services.tarefa.datetime", Relogio)
    with TestClient(app, headers=autenticacao_temporaria["headers"]) as cliente:
        criada = cliente.post(
            "/rotatividades/",
            json={
                "fk_casa_id": ambiente["casa_id"],
                "nome": "Roleta de dia fixo",
                "peso": 2,
                "prazo_dias": 1,
                "atraso_maximo": 1,
                "modo_prazo": "dia_fixo",
                "dias_semana": [relogio[0].isoweekday()],
                "intervalo_semanas": 1,
                "participantes": [ambiente["administrador_id"], ambiente["participante_id"]],
                "usar_roleta": True,
            },
        )
        assert criada.status_code == 201, criada.text
        assert criada.json()["usar_roleta"]
        id_rotatividade = criada.json()["id"]
        ocorrencias = (
            supabase.table("tarefa")
            .select("*")
            .eq("rotatividade_id", id_rotatividade)
            .order("ocorrencia_em")
            .execute()
        ).data
        assert len(ocorrencias) == 9
        yield cliente, supabase, ambiente, ocorrencias, relogio


def test_giros_concorrentes_confirmam_um_responsavel_no_supabase(cenario_roleta, monkeypatch):
    cliente, supabase, ambiente, ocorrencias, relogio = cenario_roleta
    tarefa = ocorrencias[0]
    url_tarefa = f"/tarefas/{tarefa['id']}"
    url_roleta = f"{url_tarefa}/roleta"
    detalhe = cliente.get(url_roleta).json()
    assert detalhe["estado"] == "aberta"
    assert instante_utc(detalhe["abre_em"]) == relogio[0]
    assert instante_utc(detalhe["expira_em"]) == relogio[0] + timedelta(hours=24)
    assert cliente.get(url_tarefa).json()["usuarios_atribuidos"] == []
    assert cliente.get(f"/tarefas/{ocorrencias[1]['id']}/roleta").json()["estado"] == "agendada"
    assert cliente.patch(url_tarefa, json={"modo_atribuicao": "aleatorio"}).status_code == 409

    barreira = Barrier(2, timeout=10)
    candidatos = iter(detalhe["candidatos"])

    def sortear(_candidatos):
        candidato = next(candidatos)
        barreira.wait()
        return candidato

    monkeypatch.setattr("services.rotatividade_agendamento.sortear_responsavel", sortear)
    with ThreadPoolExecutor(max_workers=2) as executor:
        a = executor.submit(cliente.post, url_roleta)
        b = executor.submit(cliente.post, url_roleta, headers=ambiente["participante_headers"])
        respostas = [a.result(), b.result()]
    for resposta in respostas:
        assert resposta.status_code == 200, resposta.text
    primeiro, segundo = [resposta.json() for resposta in respostas]
    assert primeiro == segundo
    assert primeiro["estado"] == "atribuida"
    assert primeiro["origem"] == "giro"
    final = cliente.get(url_tarefa).json()
    assert final["usuarios_atribuidos"] == [primeiro["responsavel_id"]]
    assert instante_utc(final["data_fim"]) == relogio[0] + timedelta(hours=24)
    atribuicoes = (
        supabase.table("atribuida").select("*").eq("fk_tarefa_id", tarefa["id"]).execute().data
    )
    assert len(atribuicoes) == 1
    assert cliente.post(url_roleta).json() == primeiro


def test_so_participante_ativo_gira_e_responsavel_aberto_nao_pode_sair(cenario_roleta):
    cliente, supabase, ambiente, ocorrencias, _ = cenario_roleta
    url = f"/tarefas/{ocorrencias[0]['id']}/roleta"
    (
        supabase.table("pertencer")
        .update({"ativo": False})
        .eq("fk_usuario_id", ambiente["administrador_id"])
        .eq("fk_casa_id", ambiente["casa_id"])
        .execute()
    )
    detalhe = cliente.get(url).json()
    assert detalhe["candidatos"] == [ambiente["participante_id"]]
    assert not detalhe["pode_girar"]
    assert cliente.post(url).status_code == 403
    giro = cliente.post(url, headers=ambiente["participante_headers"])
    assert giro.status_code == 200, giro.text
    assert giro.json()["responsavel_id"] == ambiente["participante_id"]
    saida = cliente.delete(
        f"/casas/{ambiente['casa_id']}/sair", headers=ambiente["participante_headers"]
    )
    assert saida.status_code == 409


@pytest.mark.parametrize("interromper_atribuicao", [False, True])
def test_job_fecha_roleta_vencida_ou_recupera_giro_confirmado(
    cenario_roleta, monkeypatch, interromper_atribuicao
):
    cliente, supabase, ambiente, ocorrencias, relogio = cenario_roleta
    tarefa = ocorrencias[0]
    url_tarefa = f"/tarefas/{tarefa['id']}"
    url_roleta = f"{url_tarefa}/roleta"
    fim = instante_utc(tarefa["roleta_expira_em"])
    configuracao = (
        supabase.table("rotatividade")
        .select("*")
        .eq("id", tarefa["rotatividade_id"])
        .execute()
        .data
    )[0]
    if interromper_atribuicao:

        def interromper(*_args):
            raise HTTPException(status_code=503, detail="Interrupção de teste.")

        monkeypatch.setattr(
            "services.rotatividade_agendamento.sortear_responsavel",
            lambda _: ambiente["participante_id"],
        )
        with monkeypatch.context() as falha:
            falha.setattr(ServicoRoletaRotatividade, "atribuir", interromper)
            assert cliente.post(url_roleta).status_code == 503
        saida = cliente.delete(
            f"/casas/{ambiente['casa_id']}/sair", headers=ambiente["participante_headers"]
        )
        assert saida.status_code == 409
        pendente = cliente.get(url_roleta).json()
        assert pendente["estado"] == "atribuindo"
        assert ambiente["participante_id"] in pendente["candidatos"]
    else:
        relogio[0] = fim
        assert cliente.get(url_roleta).json()["estado"] == "expirada"
        assert cliente.post(url_roleta).status_code == 409

    # O job diário pode atrasar ou ficar indisponível. A ocorrência já está no passado.
    relogio[0] = fim + timedelta(days=2)
    servico = ServicoAgendamentoRotatividade(supabase)
    servico._processar_roletas(configuracao, relogio[0])
    servico._processar_roletas(configuracao, relogio[0])
    final = cliente.get(url_tarefa).json()
    assert final["estado_atual"] == "pendente"
    assert final["usuarios_atribuidos"] == [
        ambiente["participante_id"] if interromper_atribuicao else ambiente["administrador_id"]
    ]
    assert final["roleta"]["origem"] == ("giro" if interromper_atribuicao else "balanceamento")
    assert instante_utc(final["data_fim"]) == relogio[0] + timedelta(hours=24)


def test_job_e_ultimo_giro_disputam_a_mesma_atribuicao(cenario_roleta, monkeypatch):
    cliente, supabase, ambiente, ocorrencias, relogio = cenario_roleta
    tarefa = ocorrencias[0]
    url = f"/tarefas/{tarefa['id']}/roleta"
    fim = instante_utc(tarefa["roleta_expira_em"])
    relogio[0] = fim - timedelta(microseconds=1)
    configuracao = (
        supabase.table("rotatividade")
        .select("*")
        .eq("id", tarefa["rotatividade_id"])
        .execute()
        .data
    )[0]
    servico = ServicoAgendamentoRotatividade(supabase)

    def fechar_janela():
        relogio[0] = fim

    barreira = Barrier(2, action=fechar_janela, timeout=10)
    decidir = ServicoRoletaRotatividade.decidir

    def decidir_em_paralelo(self, *args):
        barreira.wait()
        return decidir(self, *args)

    monkeypatch.setattr(ServicoRoletaRotatividade, "decidir", decidir_em_paralelo)
    monkeypatch.setattr(
        "services.rotatividade_agendamento.sortear_responsavel",
        lambda _: ambiente["participante_id"],
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        job = executor.submit(servico._processar_roletas, configuracao, fim)
        giro = executor.submit(cliente.post, url)
        job.result()
        resposta = giro.result()
    assert resposta.status_code == 200, resposta.text
    resultado = cliente.get(url).json()
    assert resultado == resposta.json()
    assert resultado["estado"] == "atribuida"
    esperado = (
        ambiente["participante_id"]
        if resultado["origem"] == "giro"
        else ambiente["administrador_id"]
    )
    assert resultado["responsavel_id"] == esperado
    assert cliente.get(f"/tarefas/{tarefa['id']}").json()["usuarios_atribuidos"] == [esperado]
