"""Contrato HTTP e serviço de push com Supabase e Expo simulados, sem rede."""

import os
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException
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
        self.filtros.append(lambda item: item[campo] > valor)
        return self

    def lte(self, campo, valor):
        self.filtros.append(lambda item: item[campo] <= valor)
        return self

    def order(self, _campo):
        return self

    def range(self, inicio, fim):
        self.intervalo = (inicio, fim)
        return self

    def execute(self):
        origem = self.banco.tarefas if self.nome == "tarefa" else self.banco.atribuicoes
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
        "data_fim": (agora + timedelta(hours=25)).isoformat(),
        "estado_atual": "pendente", "aviso_enviado_em": None,
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
    assert envios[0][3] == {"tarefa_id": tarefa["id"], "casa_id": tarefa["fk_casa_id"]}
    assert tarefa["aviso_enviado_em"] == agora.isoformat()
    assert servico.avisar_vencimentos(agora)["tarefas_elegiveis"] == 0
    assert len(envios) == 1


def test_job_marca_tentativa_sem_reenviar_quando_expo_falha(monkeypatch):
    agora = datetime(2026, 10, 19, 3, 5, tzinfo=timezone.utc)
    tarefa = {
        "id": str(uuid4()), "fk_casa_id": str(uuid4()),
        "data_fim": (agora + timedelta(hours=1)).isoformat(),
        "estado_atual": "atrasada", "aviso_enviado_em": None,
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
