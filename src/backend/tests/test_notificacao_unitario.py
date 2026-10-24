"""Contrato HTTP e serviço de push com Supabase e Expo simulados, sem rede."""

import os
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_KEY", "unit-test-placeholder")

from core.autenticacao import obter_usuario_atual  # noqa: E402
from core.database import get_supabase  # noqa: E402
from routers.usuario import router  # noqa: E402
from schemas.notificacao import DispositivoPushRegistrar  # noqa: E402
from services.notificacao import ServicoNotificacao  # noqa: E402
import services.notificacao as modulo_notificacao  # noqa: E402


class BancoPush:
    def __init__(self):
        self.dispositivos = []
        self.upserts = []

    def table(self, tabela):
        assert tabela == "dispositivo_push"
        return ConsultaPush(self)


class ConsultaPush:
    def __init__(self, banco):
        self.banco = banco
        self.filtros = []
        self.usuarios = None
        self.intervalo = None
        self.operacao = "select"

    def upsert(self, dados, *, on_conflict):
        self.operacao = "upsert"
        self.dados = dados
        self.conflito = on_conflict
        self.banco.upserts.append(deepcopy(dados))
        return self

    def delete(self):
        self.operacao = "delete"
        return self

    def select(self, _campos):
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor))
        return self

    def in_(self, campo, valores):
        assert campo == "fk_usuario_id"
        self.usuarios = valores
        return self

    def order(self, campo):
        assert campo == "id"
        return self

    def range(self, inicio, fim):
        self.intervalo = (inicio, fim)
        return self

    def execute(self):
        if self.operacao == "upsert":
            existente = next(
                (
                    d for d in self.banco.dispositivos
                    if d[self.conflito] == self.dados[self.conflito]
                ),
                None,
            )
            if existente is None:
                existente = {
                    "id": str(uuid4()),
                    "criado_em": datetime.now(timezone.utc).isoformat(),
                }
                self.banco.dispositivos.append(existente)
            existente.update(self.dados)
            return SimpleNamespace(data=[deepcopy(existente)])

        registros = [
            d for d in self.banco.dispositivos
            if all(d[campo] == valor for campo, valor in self.filtros)
            and (self.usuarios is None or d["fk_usuario_id"] in self.usuarios)
        ]
        if self.operacao == "delete":
            for registro in registros:
                self.banco.dispositivos.remove(registro)
        else:
            registros.sort(key=lambda d: d["id"])
            if self.intervalo is not None:
                inicio, fim = self.intervalo
                registros = registros[inicio : fim + 1]
        return SimpleNamespace(data=deepcopy(registros))


@pytest.fixture
def banco():
    return BancoPush()


@pytest.fixture(autouse=True)
def expo(monkeypatch):
    post = Mock(side_effect=AssertionError("Chamada HTTP não simulada."))
    monkeypatch.setattr(modulo_notificacao.httpx, "post", post)
    return post


@pytest.fixture
def dispositivo(banco):
    def criar(usuario=None, plataforma="android"):
        return ServicoNotificacao(banco).registrar_dispositivo(
            usuario or uuid4(),
            DispositivoPushRegistrar(
                token=f"ExpoPushToken[{uuid4().hex}]", plataforma=plataforma
            ),
        )
    return criar


@pytest.fixture
def ambiente(banco):
    app = FastAPI()
    app.include_router(router)
    usuario = uuid4()
    app.dependency_overrides[get_supabase] = lambda: banco
    app.dependency_overrides[obter_usuario_atual] = lambda: SimpleNamespace(id=usuario)
    with TestClient(app) as cliente:
        yield cliente, usuario, app


def resposta_expo(conteudo, status=200):
    return httpx.Response(
        status,
        json=conteudo,
        request=httpx.Request("POST", "https://exp.host/--/api/v2/push/send"),
    )


def test_cadastro_repetido_preserva_identidade_e_outros_dispositivos(banco, dispositivo):
    usuario = uuid4()
    primeiro = dispositivo(usuario)
    outro = dispositivo(usuario, "ios")

    repetido = ServicoNotificacao(banco).registrar_dispositivo(
        usuario,
        DispositivoPushRegistrar(token=primeiro["token"], plataforma="android"),
    )

    assert repetido == primeiro
    assert len(banco.dispositivos) == 2
    assert outro in banco.dispositivos
    assert set(banco.upserts[-1]) == {"fk_usuario_id", "token", "plataforma"}


def test_troca_de_conta_reassocia_token_e_logout_antigo_nao_remove(banco, dispositivo):
    anterior, atual = uuid4(), uuid4()
    original = dispositivo(anterior)
    servico = ServicoNotificacao(banco)

    reassociado = servico.registrar_dispositivo(
        atual, DispositivoPushRegistrar(token=original["token"], plataforma="ios")
    )
    servico.remover_dispositivo(anterior, original["token"])

    assert len(banco.dispositivos) == 1
    assert reassociado["id"] == original["id"]
    assert reassociado["criado_em"] == original["criado_em"]
    assert banco.dispositivos[0]["fk_usuario_id"] == str(atual)
    assert banco.dispositivos[0]["plataforma"] == "ios"


def test_remocao_repetida_preserva_outros_aparelhos_e_usuarios(banco, dispositivo):
    usuario = uuid4()
    removido = dispositivo(usuario)
    mesmo_usuario = dispositivo(usuario)
    outro_usuario = dispositivo()
    servico = ServicoNotificacao(banco)

    servico.remover_dispositivo(usuario, removido["token"])
    servico.remover_dispositivo(usuario, removido["token"])

    assert banco.dispositivos == [mesmo_usuario, outro_usuario]


def test_cadastro_sem_confirmacao_do_banco_falha():
    banco = Mock()
    banco.table.return_value.upsert.return_value.execute.return_value.data = []
    with pytest.raises(HTTPException) as erro:
        ServicoNotificacao(banco).registrar_dispositivo(
            uuid4(),
            DispositivoPushRegistrar(token=f"ExpoPushToken[{uuid4().hex}]", plataforma="ios"),
        )
    assert erro.value.status_code == 503


def test_rota_registra_usuario_da_sessao_sem_expor_token(ambiente, banco):
    cliente, usuario, _ = ambiente
    dados = {"token": f"ExponentPushToken[{uuid4().hex}]", "plataforma": "ios"}

    primeira = cliente.post("/usuarios/eu/dispositivos", json=dados)
    segunda = cliente.post("/usuarios/eu/dispositivos", json=dados)

    assert primeira.status_code == segunda.status_code == 200
    assert primeira.json() == segunda.json()
    assert set(primeira.json()) == {"id", "plataforma", "criado_em"}
    assert banco.dispositivos[0]["fk_usuario_id"] == str(usuario)
    assert len(banco.dispositivos) == 1


@pytest.mark.parametrize("metodo", ["POST", "DELETE"])
def test_rotas_exigem_autenticacao(ambiente, banco, metodo):
    cliente, _, app = ambiente
    app.dependency_overrides.pop(obter_usuario_atual)
    dados = {"token": f"ExpoPushToken[{uuid4().hex}]"}
    if metodo == "POST":
        dados["plataforma"] = "android"

    resposta = cliente.request(metodo, "/usuarios/eu/dispositivos", json=dados)

    assert resposta.status_code == 401
    assert banco.dispositivos == []


@pytest.mark.parametrize(
    "alteracao",
    [
        {"token": ""}, {"token": "nao-e-token-expo"},
        {"token": "ExpoPushToken[]"}, {"token": "ExpoPushToken[com espaco]"},
        {"plataforma": "web"}, {"fk_usuario_id": str(uuid4())},
    ],
)
def test_rota_rejeita_dados_invalidos_e_usuario_escolhido_no_corpo(ambiente, banco, alteracao):
    cliente, _, _ = ambiente
    dados = {"token": f"ExpoPushToken[{uuid4().hex}]", "plataforma": "android", **alteracao}

    resposta = cliente.post("/usuarios/eu/dispositivos", json=dados)

    assert resposta.status_code == 422
    assert banco.dispositivos == []


def test_rota_delete_so_remove_token_do_usuario_e_aceita_repeticao(ambiente, banco, dispositivo):
    cliente, usuario, _ = ambiente
    proprio = dispositivo(usuario)
    alheio = dispositivo()

    for token in [alheio["token"], proprio["token"], proprio["token"]]:
        resposta = cliente.request("DELETE", "/usuarios/eu/dispositivos", json={"token": token})
        assert resposta.status_code == 204
        assert resposta.content == b""

    assert banco.dispositivos == [alheio]


@pytest.mark.parametrize("usuarios", [[], [uuid4()]])
def test_sem_destinatarios_nao_chama_expo(banco, expo, usuarios):
    resultado = ServicoNotificacao(banco).enviar_push(usuarios, "Aviso", "Mensagem")
    assert resultado == {"aceitos": [], "invalidos": [], "falhas": []}
    expo.assert_not_called()


def test_envio_pagina_dispositivos_filtra_usuarios_e_divide_101_tokens(banco, dispositivo, expo):
    usuario = uuid4()
    cadastrados = [dispositivo(usuario) for _ in range(101)]
    alheio = dispositivo()

    def aceitar(_url, **kwargs):
        return resposta_expo({"data": [
            {"status": "ok", "id": str(uuid4())} for _ in kwargs["json"]
        ]})

    expo.side_effect = aceitar
    resultado = ServicoNotificacao(banco).enviar_push(
        [usuario, usuario], "Aviso", "A tarefa começa amanhã.", {"tarefa_id": str(uuid4())}
    )

    assert [len(c.kwargs["json"]) for c in expo.call_args_list] == [100, 1]
    mensagens = [m for c in expo.call_args_list for m in c.kwargs["json"]]
    assert {m["to"] for m in mensagens} == {d["token"] for d in cadastrados}
    assert all(m["title"] == "Aviso" and m["body"] == "A tarefa começa amanhã." for m in mensagens)
    assert all("tarefa_id" in m["data"] for m in mensagens)
    assert all(c.kwargs["timeout"] == 10 for c in expo.call_args_list)
    assert all(c.args == ("https://exp.host/--/api/v2/push/send",) for c in expo.call_args_list)
    assert len(resultado["aceitos"]) == 101
    assert {a["dispositivo_id"] for a in resultado["aceitos"]} == {d["id"] for d in cadastrados}
    assert resultado["invalidos"] == resultado["falhas"] == []
    assert alheio in banco.dispositivos


def test_sucesso_parcial_remove_apenas_device_not_registered(banco, dispositivo, expo):
    usuario = uuid4()
    for _ in range(3):
        dispositivo(usuario)
    ordenados = sorted(banco.dispositivos, key=lambda d: d["id"])
    ticket_id = str(uuid4())
    expo.side_effect = None
    expo.return_value = resposta_expo({"data": [
        {"status": "ok", "id": ticket_id},
        {"status": "error", "details": {"error": "DeviceNotRegistered"}},
        {"status": "error", "details": {"error": "MessageTooBig"}},
    ]})

    resultado = ServicoNotificacao(banco).enviar_push([usuario], "Aviso", "Mensagem")

    assert resultado == {
        "aceitos": [{"dispositivo_id": ordenados[0]["id"], "ticket_id": ticket_id}],
        "invalidos": [ordenados[1]["id"]],
        "falhas": [{"dispositivo_id": ordenados[2]["id"], "erro": "EnvioRecusado"}],
    }
    assert {d["id"] for d in banco.dispositivos} == {ordenados[0]["id"], ordenados[2]["id"]}
    assert all(d["token"] not in str(resultado) for d in ordenados)


@pytest.mark.parametrize(
    "falha",
    [
        httpx.ReadTimeout("timeout simulado"), httpx.ConnectError("falha simulada"),
        resposta_expo({}, 429), resposta_expo({}, 500),
        resposta_expo({"errors": [{"code": "UNAUTHORIZED"}]}, 401),
        resposta_expo({"data": []}), resposta_expo({"data": "invalida"}),
        resposta_expo({"data": [{"status": "ok", "id": str(uuid4())}], "errors": [{}]}),
        resposta_expo([{"status": "ok"}]),
        resposta_expo({"data": [{"status": "ok"}]}),
        resposta_expo({"data": [None]}),
        httpx.Response(200, text="nao e JSON", request=httpx.Request("POST", "https://exp.host")),
    ],
    ids=["timeout", "rede", "429", "500", "401", "tickets-ausentes", "data-invalida",
         "erro-no-envelope", "corpo-invalido", "ticket-sem-id", "ticket-invalido", "json-invalido"],
)
def test_falha_de_envio_preserva_dispositivo_e_nao_repete_requisicao(
    banco, dispositivo, expo, falha
):
    usuario = uuid4()
    registrado = dispositivo(usuario)
    expo.side_effect = falha if isinstance(falha, Exception) else None
    expo.return_value = falha

    resultado = ServicoNotificacao(banco).enviar_push([usuario], "Aviso", "Mensagem")

    assert resultado == {
        "aceitos": [], "invalidos": [],
        "falhas": [{"dispositivo_id": registrado["id"], "erro": "EnvioNaoConfirmado"}],
    }
    assert banco.dispositivos == [registrado]
    expo.assert_called_once()


def test_falha_no_segundo_lote_preserva_sucessos_do_primeiro(banco, dispositivo, expo):
    usuario = uuid4()
    for _ in range(101):
        dispositivo(usuario)
    ordenados = sorted(banco.dispositivos, key=lambda d: d["id"])
    expo.side_effect = [
        resposta_expo({"data": [{"status": "ok", "id": str(uuid4())} for _ in range(100)]}),
        httpx.ReadTimeout("timeout simulado"),
    ]

    resultado = ServicoNotificacao(banco).enviar_push([usuario], "Aviso", "Mensagem")

    assert len(resultado["aceitos"]) == 100
    assert resultado["falhas"] == [
        {"dispositivo_id": ordenados[-1]["id"], "erro": "EnvioNaoConfirmado"}
    ]
    assert len(banco.dispositivos) == 101
    assert expo.call_count == 2


def test_limpeza_do_primeiro_lote_nao_pula_dispositivos_da_proxima_pagina(
    banco, dispositivo, expo
):
    usuario = uuid4()
    for _ in range(101):
        dispositivo(usuario)
    ultimo = max(banco.dispositivos, key=lambda d: d["id"])
    ticket_id = str(uuid4())
    expo.side_effect = [
        resposta_expo({"data": [
            {"status": "error", "details": {"error": "DeviceNotRegistered"}}
            for _ in range(100)
        ]}),
        resposta_expo({"data": [{"status": "ok", "id": ticket_id}]}),
    ]

    resultado = ServicoNotificacao(banco).enviar_push([usuario], "Aviso", "Mensagem")

    assert len(resultado["invalidos"]) == 100
    assert resultado["aceitos"] == [{"dispositivo_id": ultimo["id"], "ticket_id": ticket_id}]
    assert resultado["falhas"] == []
    assert banco.dispositivos == [ultimo]


class BancoAvisos:
    def __init__(self, tarefas, atribuicoes):
        self.tarefas = tarefas
        self.atribuicoes = atribuicoes
        self.antes_de_atualizar = None

    def table(self, nome):
        return ConsultaAvisos(self, nome)


class ConsultaAvisos:
    def __init__(self, banco, nome):
        self.banco, self.nome = banco, nome
        self.filtros = []
        self.intervalo = None
        self.alteracao = None

    def select(self, _campos):
        return self

    def update(self, dados):
        self.alteracao = dados
        return self

    def eq(self, campo, valor):
        self.filtros.append(lambda item: item[campo] == valor)
        return self

    def in_(self, campo, valores):
        self.filtros.append(lambda item: item[campo] in valores)
        return self

    def is_(self, campo, _valor):
        self.filtros.append(lambda item: item.get(campo) is None)
        return self

    def gt(self, campo, valor):
        self.filtros.append(lambda item: item.get(campo) is not None and item[campo] > valor)
        return self

    def lte(self, campo, valor):
        self.filtros.append(lambda item: item.get(campo) is not None and item[campo] <= valor)
        return self

    def order(self, _campo):
        return self

    def range(self, inicio, fim):
        self.intervalo = (inicio, fim)
        return self

    def execute(self):
        origem = self.banco.tarefas if self.nome == "tarefa" else self.banco.atribuicoes
        if self.alteracao is not None and self.banco.antes_de_atualizar:
            self.banco.antes_de_atualizar()
        registros = [item for item in origem if all(filtro(item) for filtro in self.filtros)]
        if self.alteracao is not None:
            for item in registros:
                item.update(self.alteracao)
        elif self.intervalo:
            inicio, fim = self.intervalo
            registros = registros[inicio:fim + 1]
        return SimpleNamespace(data=deepcopy(registros))


def test_job_avisa_so_tarefas_abertas_no_horizonte_e_nao_repete(monkeypatch):
    agora = datetime(2026, 10, 19, 3, 5, tzinfo=timezone.utc)
    responsavel = uuid4()
    tarefa = {
        "id": str(uuid4()), "fk_casa_id": str(uuid4()),
        "data_fim": (agora + timedelta(hours=12)).isoformat(),
        "estado_atual": "pendente", "aviso_enviado_em": None,
        "aviso_atraso_enviado_em": None, "atraso_maximo": 2,
    }
    banco = BancoAvisos([
        tarefa,
        {**tarefa, "id": str(uuid4()), "estado_atual": "finalizado"},
        {**tarefa, "id": str(uuid4()), "data_fim": (agora + timedelta(hours=26)).isoformat()},
    ], [{"fk_tarefa_id": tarefa["id"], "fk_usuario_id": str(responsavel)}])
    envios = []

    def enviar(_self, usuarios, titulo, mensagem, dados):
        envios.append((usuarios, titulo, mensagem, dados))
        return {
            "aceitos": [{"dispositivo_id": "d", "ticket_id": "t"}],
            "falhas": [],
            "invalidos": [],
        }

    monkeypatch.setattr(ServicoNotificacao, "enviar_push", enviar)
    servico = ServicoNotificacao(banco)

    assert servico.avisar_vencimentos(agora) == {
        "tarefas_elegiveis": 1, "avisos_enviados": 1, "falhas": 0,
    }
    assert envios[0][0] == [responsavel]
    assert envios[0][1] == "Sua tarefa vence hoje"
    assert envios[0][2] == "A tarefa vence hoje e já pode ser concluída."
    assert envios[0][3] == {
        "tipo": "tarefa_vence_hoje",
        "tarefa_id": tarefa["id"],
        "casa_id": tarefa["fk_casa_id"],
    }
    assert tarefa["aviso_enviado_em"] == agora.isoformat()
    assert servico.avisar_vencimentos(agora)["tarefas_elegiveis"] == 0
    assert len(envios) == 1


def test_job_marca_tentativa_sem_reenviar_quando_expo_falha(monkeypatch):
    agora = datetime(2026, 10, 19, 3, 5, tzinfo=timezone.utc)
    tarefa = {
        "id": str(uuid4()), "fk_casa_id": str(uuid4()),
        "data_fim": (agora + timedelta(hours=1)).isoformat(),
        "estado_atual": "atrasada", "aviso_enviado_em": None,
        "aviso_atraso_enviado_em": None, "atraso_maximo": 2,
    }
    banco = BancoAvisos([tarefa], [
        {"fk_tarefa_id": tarefa["id"], "fk_usuario_id": str(uuid4())}
    ])
    chamadas = []

    def falhar(*_args):
        chamadas.append(True)
        return {
            "aceitos": [],
            "falhas": [{"dispositivo_id": "d", "erro": "EnvioNaoConfirmado"}],
            "invalidos": [],
        }

    monkeypatch.setattr(ServicoNotificacao, "enviar_push", falhar)
    servico = ServicoNotificacao(banco)
    assert servico.avisar_vencimentos(agora)["falhas"] == 1
    assert servico.avisar_vencimentos(agora)["tarefas_elegiveis"] == 0
    assert chamadas == [True]




def test_job_avisa_tarefa_atrasada_apenas_dentro_da_tolerancia(monkeypatch):
    agora = datetime(2026, 10, 19, 3, 5, tzinfo=timezone.utc)
    responsavel = uuid4()
    elegivel = {
        "id": str(uuid4()), "fk_casa_id": str(uuid4()),
        "data_fim": (agora - timedelta(hours=2)).isoformat(),
        "estado_atual": "atrasada", "aviso_enviado_em": None,
        "aviso_atraso_enviado_em": None, "atraso_maximo": 2,
    }
    expirou = {
        **elegivel, "id": str(uuid4()),
        "data_fim": (agora - timedelta(days=3)).isoformat(),
        "atraso_maximo": 2,
    }
    banco = BancoAvisos([elegivel, expirou], [
        {"fk_tarefa_id": elegivel["id"], "fk_usuario_id": str(responsavel)},
        {"fk_tarefa_id": expirou["id"], "fk_usuario_id": str(responsavel)},
    ])
    envios = []

    def enviar(_self, usuarios, titulo, mensagem, dados):
        envios.append((usuarios, titulo, mensagem, dados))
        return {"aceitos": [{"dispositivo_id": "d", "ticket_id": "t"}],
                "falhas": [], "invalidos": []}

    monkeypatch.setattr(ServicoNotificacao, "enviar_push", enviar)
    servico = ServicoNotificacao(banco)

    assert servico.avisar_vencimentos(agora) == {
        "tarefas_elegiveis": 1, "avisos_enviados": 1, "falhas": 0,
    }
    assert envios[0][1] == "Sua tarefa está atrasada"
    assert envios[0][2] == "A tarefa está atrasada, mas ainda pode ser concluída."
    assert envios[0][3] == {
        "tipo": "tarefa_atrasada",
        "tarefa_id": elegivel["id"],
        "casa_id": elegivel["fk_casa_id"],
    }
    assert elegivel["aviso_atraso_enviado_em"] == agora.isoformat()
    assert expirou["aviso_atraso_enviado_em"] is None
    assert servico.avisar_vencimentos(agora)["tarefas_elegiveis"] == 0
    assert len(envios) == 1


def test_aviso_de_vencimento_nao_e_enviado_antes_do_inicio_da_tarefa(monkeypatch):
    agora = datetime(2026, 10, 19, 3, 5, tzinfo=timezone.utc)
    tarefa = {
        "id": str(uuid4()), "fk_casa_id": str(uuid4()),
        "data_inicio": (agora + timedelta(hours=1)).isoformat(),
        "data_fim": (agora + timedelta(hours=12)).isoformat(),
        "estado_atual": "pendente", "aviso_enviado_em": None,
        "aviso_atraso_enviado_em": None, "atraso_maximo": 2,
    }
    banco = BancoAvisos([tarefa], [
        {"fk_tarefa_id": tarefa["id"], "fk_usuario_id": str(uuid4())}
    ])
    enviar = Mock()
    monkeypatch.setattr(ServicoNotificacao, "enviar_push", enviar)

    assert ServicoNotificacao(banco).avisar_vencimentos(agora) == {
        "tarefas_elegiveis": 0, "avisos_enviados": 0, "falhas": 0,
    }
    assert tarefa["aviso_enviado_em"] is None
    enviar.assert_not_called()


def test_push_inclui_categoria_de_acoes_para_notificacoes_de_prazo(banco, dispositivo, expo):
    usuario = uuid4()
    dispositivo(usuario)
    expo.return_value = resposta_expo({"data": [{"status": "ok", "id": str(uuid4())}]})

    ServicoNotificacao(banco).enviar_push(
        [usuario], "Sua tarefa vence hoje", "Mensagem",
        {"tipo": "tarefa_vence_hoje", "tarefa_id": str(uuid4()), "casa_id": str(uuid4())},
    )

    mensagem = expo.call_args.kwargs["json"][0]
    assert mensagem["categoryId"] == "tarefa_pendente"
    assert mensagem["data"]["tipo"] == "tarefa_vence_hoje"


def tarefa_com_inicio(agora, **alteracoes):
    return {
        "id": str(uuid4()), "fk_casa_id": str(uuid4()),
        "data_inicio": (agora + timedelta(hours=12)).isoformat(),
        "estado_atual": "pendente", "rotatividade_id": None,
        "aviso_inicio_tentado_em": None, "aviso_enviado_em": "aviso-de-vencimento-existente",
        **alteracoes,
    }


@pytest.fixture
def envio_normal(monkeypatch):
    enviar = Mock(return_value={
        "aceitos": [{"dispositivo_id": str(uuid4()), "ticket_id": str(uuid4())}],
        "invalidos": [], "falhas": [],
    })
    monkeypatch.setattr(ServicoNotificacao, "enviar_push", enviar)
    return enviar


def test_inicio_respeita_limites_estado_e_marcacao_sem_afetar_vencimento(envio_normal):
    agora = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
    usuario = str(uuid4())
    alteracoes = [
        {"data_inicio": agora.isoformat()},
        {"data_inicio": (agora + timedelta(microseconds=1)).isoformat()},
        {"data_inicio": (agora + timedelta(hours=24)).isoformat()},
        {"data_inicio": (agora + timedelta(hours=24, microseconds=1)).isoformat()},
        {"data_inicio": (agora - timedelta(hours=1)).isoformat()},
        {"data_inicio": None}, {"estado_atual": "finalizado"},
        {"estado_atual": "nao_feito"}, {"estado_atual": "atrasada"},
        {"aviso_inicio_tentado_em": agora.isoformat()},
    ]
    tarefas = [tarefa_com_inicio(agora, **mudanca) for mudanca in alteracoes]
    banco = BancoAvisos(tarefas, [
        {"fk_tarefa_id": t["id"], "fk_usuario_id": usuario} for t in tarefas
    ])
    servico = ServicoNotificacao(banco)

    assert servico.avisar_inicios(agora) == {
        "tarefas_elegiveis": 2, "avisos_enviados": 2, "falhas": 0,
    }
    assert {c.args[3]["tarefa_id"] for c in envio_normal.call_args_list} == {
        tarefas[1]["id"], tarefas[2]["id"],
    }
    assert all(c.args[0] == [UUID(usuario)] for c in envio_normal.call_args_list)
    assert all(c.args[3]["tipo"] == "inicio_tarefa" for c in envio_normal.call_args_list)
    assert all(t["aviso_enviado_em"] == "aviso-de-vencimento-existente" for t in tarefas)
    assert servico.avisar_inicios(agora)["tarefas_elegiveis"] == 0
    assert envio_normal.call_count == 2


def test_inicio_sem_responsavel_nao_reserva_nem_envia(envio_normal):
    agora = datetime.now(timezone.utc)
    tarefa = tarefa_com_inicio(agora)
    resultado = ServicoNotificacao(BancoAvisos([tarefa], [])).avisar_inicios(agora)
    assert resultado == {"tarefas_elegiveis": 1, "avisos_enviados": 0, "falhas": 0}
    assert tarefa["aviso_inicio_tentado_em"] is None
    envio_normal.assert_not_called()


@pytest.mark.parametrize("alteracao", ["marcacao", "estado", "inicio"])
def test_reserva_de_inicio_nao_sobrescreve_mudanca_concorrente(envio_normal, alteracao):
    agora = datetime.now(timezone.utc)
    tarefa = tarefa_com_inicio(agora)
    banco = BancoAvisos([tarefa], [
        {"fk_tarefa_id": tarefa["id"], "fk_usuario_id": str(uuid4())}
    ])
    mudancas = {
        "marcacao": {"aviso_inicio_tentado_em": agora.isoformat()},
        "estado": {"estado_atual": "finalizado"},
        "inicio": {"data_inicio": (agora + timedelta(days=2)).isoformat()},
    }
    banco.antes_de_atualizar = lambda: tarefa.update(mudancas[alteracao])

    assert ServicoNotificacao(banco).avisar_inicios(agora)["avisos_enviados"] == 0
    envio_normal.assert_not_called()


def test_inicio_processa_todas_as_paginas_antes_de_marcar(envio_normal):
    agora = datetime.now(timezone.utc)
    tarefas = [tarefa_com_inicio(agora) for _ in range(101)]
    banco = BancoAvisos(tarefas, [
        {"fk_tarefa_id": t["id"], "fk_usuario_id": str(uuid4())} for t in tarefas
    ])

    assert ServicoNotificacao(banco).avisar_inicios(agora)["avisos_enviados"] == 101
    assert all(t["aviso_inicio_tentado_em"] == agora.isoformat() for t in tarefas)
    assert envio_normal.call_count == 101


def test_rodizio_agrupa_por_usuario_e_casa_sem_avisar_ocorrencias_distantes(envio_normal):
    agora = datetime.now(timezone.utc)
    casa, outra_casa, usuario, outro_usuario = [str(uuid4()) for _ in range(4)]
    rotatividade = str(uuid4())
    tarefas = [
        tarefa_com_inicio(agora, fk_casa_id=casa, rotatividade_id=rotatividade),
        tarefa_com_inicio(agora, fk_casa_id=casa, rotatividade_id=rotatividade),
        tarefa_com_inicio(agora, fk_casa_id=outra_casa, rotatividade_id=rotatividade),
        tarefa_com_inicio(agora, fk_casa_id=casa, rotatividade_id=rotatividade),
        tarefa_com_inicio(agora, fk_casa_id=casa),
        tarefa_com_inicio(
            agora, fk_casa_id=casa, rotatividade_id=rotatividade,
            data_inicio=(agora + timedelta(days=60)).isoformat(),
        ),
    ]
    banco = BancoAvisos(tarefas, [
        {"fk_tarefa_id": t["id"], "fk_usuario_id": outro_usuario if i == 3 else usuario}
        for i, t in enumerate(tarefas)
    ])

    assert ServicoNotificacao(banco).avisar_inicios(agora) == {
        "tarefas_elegiveis": 5, "avisos_enviados": 4, "falhas": 0,
    }
    resumos = [c for c in envio_normal.call_args_list if c.args[3]["tipo"] == "rodizio_distribuido"]
    assert len(resumos) == 3
    resumo_principal = next(
        c for c in resumos if c.args[0] == [UUID(usuario)] and c.args[3]["casa_id"] == casa
    )
    assert "2 tarefas" in resumo_principal.args[2]
    assert all("tarefa_id" not in c.args[3] for c in resumos)
    assert tarefas[-1]["aviso_inicio_tentado_em"] is None


def test_inicio_isola_falha_inesperada_e_nao_repete_tentativa(envio_normal, caplog):
    agora = datetime.now(timezone.utc)
    tarefas = [tarefa_com_inicio(agora) for _ in range(2)]
    banco = BancoAvisos(tarefas, [
        {"fk_tarefa_id": t["id"], "fk_usuario_id": str(uuid4())} for t in tarefas
    ])
    detalhe_privado = uuid4().hex
    envio_normal.side_effect = RuntimeError(detalhe_privado)
    servico = ServicoNotificacao(banco)

    assert servico.avisar_inicios(agora) == {
        "tarefas_elegiveis": 2, "avisos_enviados": 0, "falhas": 2,
    }
    assert servico.avisar_inicios(agora)["tarefas_elegiveis"] == 0
    assert envio_normal.call_count == 2
    assert detalhe_privado not in caplog.text


def test_aviso_de_evento_aguarda_segundo_plano_e_preserva_destinatarios(envio_normal):
    tarefa = tarefa_com_inicio(datetime.now(timezone.utc))
    usuario = str(uuid4())
    destinatarios = [usuario]
    tarefas_fundo = BackgroundTasks()
    servico = ServicoNotificacao(object(), tarefas_fundo)

    servico.notificar_tarefa("tarefa_atribuida", tarefa, destinatarios)
    destinatarios.clear()
    tarefa["fk_casa_id"] = str(uuid4())
    envio_normal.assert_not_called()
    assert len(tarefas_fundo.tasks) == 1
    agendada = tarefas_fundo.tasks[0]
    agendada.func(*agendada.args, **agendada.kwargs)

    assert envio_normal.call_args.args[0] == [UUID(usuario)]
    assert envio_normal.call_args.args[3]["tipo"] == "tarefa_atribuida"
    assert envio_normal.call_args.args[3]["casa_id"] != tarefa["fk_casa_id"]


def test_falha_na_preparacao_do_aviso_nao_se_propaga(envio_normal, caplog):
    banco = Mock()
    detalhe_privado = uuid4().hex
    banco.table.side_effect = RuntimeError(detalhe_privado)
    ServicoNotificacao(banco).notificar_tarefa("prazo_encerrado", {"id": str(uuid4())})
    envio_normal.assert_not_called()
    assert detalhe_privado not in caplog.text


def test_reinicio_de_aviso_ocorre_em_segundo_plano_sem_alterar_marcacao_de_vencimento():
    agora = datetime.now(timezone.utc)
    tarefa = tarefa_com_inicio(agora, aviso_inicio_tentado_em=agora.isoformat())
    banco = BancoAvisos([tarefa], [])
    tarefas_fundo = BackgroundTasks()
    ServicoNotificacao(banco, tarefas_fundo).reiniciar_aviso_inicio(tarefa)
    assert tarefa["aviso_inicio_tentado_em"] == agora.isoformat()

    agendada = tarefas_fundo.tasks[0]
    agendada.func(*agendada.args)

    assert tarefa["aviso_inicio_tentado_em"] is None
    assert tarefa["aviso_enviado_em"] == "aviso-de-vencimento-existente"


def test_reinicio_falhando_ou_desatualizado_nao_altera_tarefa_nem_propaga_erro(caplog):
    agora = datetime.now(timezone.utc)
    tarefa = tarefa_com_inicio(agora, aviso_inicio_tentado_em=agora.isoformat())
    anterior = {**tarefa, "data_inicio": (agora + timedelta(hours=1)).isoformat()}
    ServicoNotificacao(BancoAvisos([tarefa], [])).reiniciar_aviso_inicio(anterior)
    assert tarefa["aviso_inicio_tentado_em"] == agora.isoformat()

    banco = Mock()
    detalhe_privado = uuid4().hex
    banco.table.side_effect = RuntimeError(detalhe_privado)
    ServicoNotificacao(banco).reiniciar_aviso_inicio(tarefa)
    assert detalhe_privado not in caplog.text
