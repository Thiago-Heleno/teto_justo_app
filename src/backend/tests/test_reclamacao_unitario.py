from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from services.reclamacao import ServicoReclamacao
from services.tarefa import ServicoTarefa
from test_contrato_casa_router_unitario import ConsultaEmMemoria, SupabaseEmMemoria
from core.autenticacao import obter_usuario_atual
from core.database import get_supabase
from routers.tarefa import router


@pytest.fixture
def cenario(monkeypatch):
    agora = datetime(2030, 1, 10, 12, tzinfo=timezone.utc)

    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):
            return agora

    monkeypatch.setattr("services.tarefa.datetime", Relogio)
    monkeypatch.setattr("services.reclamacao.datetime", Relogio)
    dono, responsavel, morador, casa_id, tarefa_id = [str(uuid4()) for _ in range(5)]
    tarefa = {
        "id": tarefa_id, "nome": "Limpar cozinha", "estado_atual": "pendente",
        "dificuldade": 2, "pontuacao": 25, "atraso_maximo": 2,
        "data_fim": (agora + timedelta(days=2)).isoformat(),
        "data_inicio": (agora - timedelta(days=1)).isoformat(),
        "fk_casa_id": casa_id, "fk_usuario_id": dono, "reaberturas": 0,
    }
    banco = SupabaseEmMemoria({
        "casa": [{"id": casa_id, "fk_usuario_id": dono, "politica_reclamacao": "votacao"}],
        "tarefa": [tarefa],
        "atribuida": [{"fk_tarefa_id": tarefa_id, "fk_usuario_id": responsavel}],
        "pertencer": [
            {"fk_casa_id": casa_id, "fk_usuario_id": usuario, "ativo": True, "score": 100}
            for usuario in [dono, responsavel, morador, str(uuid4()), str(uuid4())]
        ],
        "score_event": [],
        "reclamacao_tarefa": [],
    })
    executar = ConsultaEmMemoria.execute

    def executar_com_unicidade(consulta):
        chaves = {
            "reclamacao_tarefa": ("fk_usuario_id", "fk_tarefa_id", "ciclo"),
            "score_event": ("fk_usuario_id", "fk_tarefa_id", "tipo", "ciclo"),
        }.get(consulta.tabela)
        if chaves and consulta.acao == "insert" and any(
            all(registro[campo] == consulta.dados[campo] for campo in chaves)
            for registro in banco.registros[consulta.tabela]
        ):
            raise APIError({"code": "23505", "message": "Registro duplicado."})
        return executar(consulta)

    monkeypatch.setattr(ConsultaEmMemoria, "execute", executar_com_unicidade)
    ServicoTarefa(banco, BackgroundTasks()).concluir_tarefa(UUID(tarefa_id), UUID(responsavel))
    return banco, ServicoReclamacao(banco, BackgroundTasks()), tarefa, UUID(morador), agora


@pytest.mark.parametrize("estado", ["pendente", "atrasada", "nao_feito"])
def test_so_aceita_reclamacao_de_tarefa_finalizada(cenario, estado):
    banco, servico, tarefa, morador, _ = cenario
    tarefa["estado_atual"] = estado

    with pytest.raises(HTTPException) as erro:
        servico.reclamar_tarefa(UUID(tarefa["id"]), morador)

    assert erro.value.status_code == 409
    assert banco.registros["reclamacao_tarefa"] == []


@pytest.mark.parametrize("concluida_em", [None, "2030-01-09T11:59:59.999999Z"])
def test_rejeita_conclusao_sem_data_ou_fora_da_janela(cenario, concluida_em):
    banco, servico, tarefa, morador, _ = cenario
    tarefa["concluida_em"] = concluida_em

    with pytest.raises(HTTPException) as erro:
        servico.reclamar_tarefa(UUID(tarefa["id"]), morador)

    assert erro.value.status_code == 409
    assert banco.registros["reclamacao_tarefa"] == []


def test_rejeita_data_de_conclusao_no_futuro(cenario):
    banco, servico, tarefa, morador, agora = cenario
    tarefa["concluida_em"] = (agora + timedelta(microseconds=1)).isoformat()

    with pytest.raises(HTTPException) as erro:
        servico.reclamar_tarefa(UUID(tarefa["id"]), morador)

    assert erro.value.status_code == 409
    assert banco.registros["reclamacao_tarefa"] == []


@pytest.mark.parametrize("vinculo", ["inativo", "ausente", "outra_casa"])
def test_so_morador_ativo_da_casa_pode_reclamar(cenario, vinculo):
    banco, servico, tarefa, morador, _ = cenario
    registro = next(v for v in banco.registros["pertencer"] if v["fk_usuario_id"] == str(morador))
    if vinculo == "inativo":
        registro["ativo"] = False
    elif vinculo == "ausente":
        banco.registros["pertencer"].remove(registro)
    else:
        registro["fk_casa_id"] = str(uuid4())

    with pytest.raises(HTTPException) as erro:
        servico.reclamar_tarefa(UUID(tarefa["id"]), morador)

    assert erro.value.status_code == 403
    assert banco.registros["reclamacao_tarefa"] == []


def test_politica_nenhuma_impede_registro(cenario):
    banco, servico, tarefa, morador, _ = cenario
    banco.registros["casa"][0]["politica_reclamacao"] = "nenhuma"

    with pytest.raises(HTTPException) as erro:
        servico.reclamar_tarefa(UUID(tarefa["id"]), morador)

    assert erro.value.status_code == 409
    assert banco.registros["reclamacao_tarefa"] == []


def test_duplicata_no_mesmo_ciclo_nao_registra_nem_reabre(cenario):
    banco, servico, tarefa, morador, _ = cenario
    servico.reclamar_tarefa(UUID(tarefa["id"]), morador)

    with pytest.raises(HTTPException) as erro:
        servico.reclamar_tarefa(UUID(tarefa["id"]), morador)

    assert erro.value.status_code == 409
    assert len(banco.registros["reclamacao_tarefa"]) == 1
    assert tarefa["estado_atual"] == "finalizado"
    assert len(banco.registros["score_event"]) == 1


def test_falha_de_persistencia_nao_e_tratada_como_duplicata(cenario, monkeypatch):
    banco, servico, tarefa, morador, _ = cenario
    executar = ConsultaEmMemoria.execute

    def executar_com_falha(consulta):
        if consulta.tabela == "reclamacao_tarefa" and consulta.acao == "insert":
            raise APIError({"code": "08006", "message": "Falha de conexão simulada."})
        return executar(consulta)

    monkeypatch.setattr(ConsultaEmMemoria, "execute", executar_com_falha)
    with pytest.raises(APIError):
        servico.reclamar_tarefa(UUID(tarefa["id"]), morador)

    assert banco.registros["reclamacao_tarefa"] == []
    assert tarefa["estado_atual"] == "finalizado"


def test_tarefa_inexistente_retorna_404(cenario):
    banco, servico, _, morador, _ = cenario

    with pytest.raises(HTTPException) as erro:
        servico.reclamar_tarefa(uuid4(), morador)

    assert erro.value.status_code == 404
    assert banco.registros["reclamacao_tarefa"] == []


def test_responsavel_nao_pode_reclamar_da_propria_tarefa(cenario):
    banco, servico, tarefa, _, _ = cenario
    responsavel = UUID(banco.registros["atribuida"][0]["fk_usuario_id"])

    with pytest.raises(HTTPException) as erro:
        servico.reclamar_tarefa(UUID(tarefa["id"]), responsavel)

    assert erro.value.status_code == 403
    assert banco.registros["reclamacao_tarefa"] == []


def test_proprietario_com_vinculo_ativo_pode_reclamar(cenario):
    banco, servico, tarefa, _, _ = cenario
    dono = UUID(banco.registros["casa"][0]["fk_usuario_id"])

    resultado = servico.reclamar_tarefa(UUID(tarefa["id"]), dono)

    assert resultado["estado_atual"] == "finalizado"
    assert banco.registros["reclamacao_tarefa"][0]["fk_usuario_id"] == str(dono)


@pytest.mark.parametrize("concluida_em", [
    "2030-01-09T12:00:00Z",
    "2030-01-09T09:00:00-03:00",
    "2030-01-09T12:00:00",
    "2030-01-09T12:00:00.000001Z",
    "2030-01-10T12:00:00Z",
])
def test_janela_inclui_conclusao_e_instante_exato_de_24h(cenario, concluida_em):
    banco, servico, tarefa, morador, _ = cenario
    tarefa["concluida_em"] = concluida_em

    servico.reclamar_tarefa(UUID(tarefa["id"]), morador)

    assert len(banco.registros["reclamacao_tarefa"]) == 1


@pytest.mark.parametrize("dias_ate_prazo,estado", [
    (2, "pendente"), (-1, "atrasada"), (-3, "nao_feito"),
])
def test_uma_reclamacao_reabre_direto_e_estorna_pontos_conforme_prazo(
    cenario, monkeypatch, dias_ate_prazo, estado,
):
    banco, servico, tarefa, morador, agora = cenario
    banco.registros["casa"][0]["politica_reclamacao"] = "uma_reclamacao"
    tarefa["data_fim"] = (agora + timedelta(days=dias_ate_prazo)).isoformat()

    def reabertura_com_autorizacao_proibida(*args):
        pytest.fail("Reclamação deve chamar o ciclo de vida diretamente.")

    monkeypatch.setattr(ServicoTarefa, "reabrir_tarefa", reabertura_com_autorizacao_proibida)
    monkeypatch.setattr(
        "services.autorizacao.ServicoAutorizacaoCasa.garantir_administrador_da_casa",
        reabertura_com_autorizacao_proibida,
    )

    resultado = servico.reclamar_tarefa(UUID(tarefa["id"]), morador)

    assert resultado["estado_atual"] == estado
    assert resultado["concluida_em"] is None
    assert tarefa["reaberturas"] == 1
    assert len(banco.registros["reclamacao_tarefa"]) == 1
    assert [(e["tipo"], e["pontuacao"]) for e in banco.registros["score_event"]] == [
        ("credito", 25), ("reversal", -25),
    ]
    assert banco.registros["pertencer"][1]["score"] == 100


@pytest.mark.parametrize("elegiveis,limite", [(1, 1), (2, 1), (3, 2), (4, 2), (5, 3)])
def test_votacao_reabre_ao_atingir_metade_arredondada_dos_demais_moradores(
    cenario, elegiveis, limite,
):
    banco, servico, tarefa, morador, _ = cenario
    responsavel = banco.registros["pertencer"][1]
    votantes = [str(morador)] + [str(uuid4()) for _ in range(elegiveis - 1)]
    banco.registros["pertencer"] = [responsavel] + [
        {"fk_casa_id": tarefa["fk_casa_id"], "fk_usuario_id": usuario, "ativo": True}
        for usuario in votantes
    ]
    banco.registros["pertencer"].extend([
        {"fk_casa_id": tarefa["fk_casa_id"], "fk_usuario_id": str(uuid4()), "ativo": False},
        {"fk_casa_id": str(uuid4()), "fk_usuario_id": str(uuid4()), "ativo": True},
    ])

    for indice, usuario in enumerate(votantes[:limite], start=1):
        resultado = servico.reclamar_tarefa(UUID(tarefa["id"]), UUID(usuario))
        assert resultado["estado_atual"] == ("pendente" if indice == limite else "finalizado")

    assert tarefa["reaberturas"] == 1
    assert len(banco.registros["reclamacao_tarefa"]) == limite
    assert responsavel["score"] == 100


def test_votos_de_outra_tarefa_ou_ciclo_nao_atingem_limite(cenario):
    banco, servico, tarefa, morador, _ = cenario
    tarefa["reaberturas"] = 1
    banco.registros["reclamacao_tarefa"] = [
        {"fk_tarefa_id": tarefa["id"], "fk_usuario_id": str(uuid4()), "ciclo": 0},
        {"fk_tarefa_id": str(uuid4()), "fk_usuario_id": str(uuid4()), "ciclo": 1},
    ]

    resultado = servico.reclamar_tarefa(UUID(tarefa["id"]), morador)

    assert resultado["estado_atual"] == "finalizado"
    assert tarefa["reaberturas"] == 1
    assert len(banco.registros["score_event"]) == 1
    assert banco.registros["reclamacao_tarefa"][-1]["ciclo"] == 1


def test_morador_pode_reclamar_novamente_apos_nova_conclusao(cenario):
    banco, servico, tarefa, morador, _ = cenario
    banco.registros["casa"][0]["politica_reclamacao"] = "uma_reclamacao"
    id_tarefa = UUID(tarefa["id"])
    responsavel = UUID(banco.registros["atribuida"][0]["fk_usuario_id"])
    servico.reclamar_tarefa(id_tarefa, morador)
    servico.tarefas.concluir_tarefa(id_tarefa, responsavel)

    resultado = servico.reclamar_tarefa(id_tarefa, morador)

    assert resultado["estado_atual"] == "pendente"
    assert tarefa["reaberturas"] == 2
    assert [r["ciclo"] for r in banco.registros["reclamacao_tarefa"]] == [0, 1]
    assert [(e["tipo"], e["ciclo"]) for e in banco.registros["score_event"]] == [
        ("credito", 0), ("reversal", 0), ("credito", 1), ("reversal", 1),
    ]


def test_reclamacoes_com_mesma_leitura_reabrem_e_estornam_uma_unica_vez(cenario, monkeypatch):
    banco, servico, tarefa, morador, _ = cenario
    banco.registros["casa"][0]["politica_reclamacao"] = "uma_reclamacao"
    original = deepcopy(tarefa)
    monkeypatch.setattr(servico.tarefas, "_buscar_tarefa_bruta", lambda _: deepcopy(original))
    servico.reclamar_tarefa(UUID(tarefa["id"]), morador)

    resultado = servico.reclamar_tarefa(UUID(tarefa["id"]), UUID(tarefa["fk_usuario_id"]))

    assert resultado["estado_atual"] == "pendente"
    assert tarefa["reaberturas"] == 1
    assert len(banco.registros["reclamacao_tarefa"]) == 2
    assert len(banco.registros["score_event"]) == 2
    assert banco.registros["pertencer"][1]["score"] == 100


def test_rota_aceita_post_sem_corpo_e_devolve_tarefa_reaberta(cenario):
    banco, _, tarefa, morador, _ = cenario
    banco.registros["casa"][0]["politica_reclamacao"] = "uma_reclamacao"
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_supabase] = lambda: banco
    app.dependency_overrides[obter_usuario_atual] = lambda: SimpleNamespace(id=morador)

    with TestClient(app) as cliente:
        resposta = cliente.post(f"/tarefas/{tarefa['id']}/reclamacoes")

    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["id"] == tarefa["id"]
    assert resposta.json()["estado_atual"] == "pendente"
    assert resposta.json()["concluida_em"] is None
    assert banco.registros["reclamacao_tarefa"][0]["fk_usuario_id"] == str(morador)


def test_rota_exige_autenticacao(cenario):
    banco, _, tarefa, _, _ = cenario
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_supabase] = lambda: banco

    with TestClient(app) as cliente:
        resposta = cliente.post(f"/tarefas/{tarefa['id']}/reclamacoes")

    assert resposta.status_code == 401
    assert banco.registros["reclamacao_tarefa"] == []
