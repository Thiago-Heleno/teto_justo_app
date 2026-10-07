"""Contrato HTTP da casa, exercitado com um Supabase em memória."""

import os
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient


load_dotenv()
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_KEY", "unit-test-placeholder")

from core.autenticacao import obter_usuario_atual  # noqa: E402
from core.database import get_supabase  # noqa: E402
from main import app  # noqa: E402
from services.limite_login import get_limitador_login  # noqa: E402


SEGREDO_TESTE = "segredo-de-teste-para-convites-da-casa-com-mais-de-32-caracteres"


class ConsultaEmMemoria:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
        self.acao = "select"
        self.campos = "*"
        self.filtros = []
        self.filtros_in = []
        self.intervalo = None
        self.ordens = []
        self.dados = None

    def select(self, campos, count=None):
        self.campos = campos
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor))
        return self

    def in_(self, campo, valores):
        self.filtros_in.append((campo, {str(valor) for valor in valores}))
        return self

    def order(self, campo, desc=False):
        self.ordens.append((campo, desc))
        return self

    def range(self, inicio, fim):
        self.intervalo = (inicio, fim)
        return self

    def limit(self, quantidade):
        self.intervalo = (0, quantidade - 1)
        return self

    def insert(self, dados):
        self.acao = "insert"
        self.dados = dados
        return self

    def update(self, dados):
        self.acao = "update"
        self.dados = dados
        return self

    def delete(self):
        self.acao = "delete"
        return self

    def _corresponde(self, registro):
        return all(
            str(registro.get(campo)) == str(valor) for campo, valor in self.filtros
        ) and all(
            str(registro.get(campo)) in valores for campo, valores in self.filtros_in
        )

    def execute(self):
        registros = self.banco.registros.setdefault(self.tabela, [])
        selecionados = [registro for registro in registros if self._corresponde(registro)]

        if self.acao == "insert":
            novos = self.dados if isinstance(self.dados, list) else [self.dados]
            selecionados = []
            for novo in novos:
                registro = deepcopy(novo)
                if self.tabela == "casa":
                    registro.setdefault("id", str(uuid4()))
                    registro.setdefault("rotacao_versao", 0)
                elif self.tabela == "pertencer":
                    registro.setdefault("ativo", True)
                registros.append(registro)
                selecionados.append(registro)
        elif self.acao == "update":
            for registro in selecionados:
                registro.update(self.dados)
        elif self.acao == "delete":
            for registro in selecionados:
                registros.remove(registro)
        else:
            for campo, decrescente in reversed(self.ordens):
                selecionados.sort(
                    key=lambda registro: str(registro[campo]), reverse=decrescente
                )
            total = len(selecionados)
            if self.intervalo is not None:
                inicio, fim = self.intervalo
                selecionados = selecionados[inicio : fim + 1]
            if self.campos != "*":
                nomes = [campo.strip() for campo in self.campos.split(",")]
                selecionados = [
                    {campo: registro[campo] for campo in nomes} for registro in selecionados
                ]
            return SimpleNamespace(data=deepcopy(selecionados), count=total)

        return SimpleNamespace(data=deepcopy(selecionados), count=len(selecionados))


class SupabaseEmMemoria:
    def __init__(self, registros):
        self.registros = registros

    def table(self, tabela):
        return ConsultaEmMemoria(self, tabela)


def casa(numero, proprietario):
    return {
        "id": str(UUID(int=numero)),
        "nome": f"Casa {numero}",
        "endereco": f"Rua {numero}",
        "foto": None,
        "fk_usuario_id": str(proprietario),
        "timezone": "America/Sao_Paulo",
        "rotacao_versao": 0,
    }


def vinculo(casa_id, usuario_id, score=0, ativo=True):
    return {
        "fk_casa_id": str(casa_id),
        "fk_usuario_id": str(usuario_id),
        "score": score,
        "ativo": ativo,
    }


@pytest.fixture
def ambiente(monkeypatch):
    proprietario = UUID(int=50)
    outro_proprietario = UUID(int=51)
    casas = {numero: UUID(int=numero) for numero in range(1, 6)}
    banco = SupabaseEmMemoria({
        "casa": [
            casa(5, outro_proprietario), casa(3, outro_proprietario),
            casa(4, proprietario), casa(2, outro_proprietario),
            casa(1, proprietario),
        ],
        "pertencer": [
            vinculo(casas[1], proprietario),  # Casa própria e vinculada não duplica.
            vinculo(casas[2], proprietario, 37),
            vinculo(casas[3], proprietario, 11, ativo=False),
            vinculo(casas[5], proprietario),
        ],
        "usuario": [{
            "id": str(proprietario), "nome": "Ana", "email": "ana@example.com",
            "telefone": None, "foto": None,
        }],
        "score_event": [],
        "atribuida": [],
        "tarefa": [],
    })
    monkeypatch.setenv("CASA_CONVITE_SECRET", SEGREDO_TESTE)
    monkeypatch.setitem(app.dependency_overrides, get_supabase, lambda: banco)
    monkeypatch.setitem(
        app.dependency_overrides,
        obter_usuario_atual,
        lambda: SimpleNamespace(id=proprietario),
    )
    with TestClient(app) as cliente:
        yield cliente, banco, casas, proprietario, outro_proprietario


def trocar_usuario(monkeypatch, usuario_id):
    monkeypatch.setitem(
        app.dependency_overrides,
        obter_usuario_atual,
        lambda: SimpleNamespace(id=usuario_id),
    )


def test_fluxo_login_criacao_convite_e_logout_com_autenticacao_real(ambiente, monkeypatch):
    import secrets

    import bcrypt

    cliente, banco, _, _, _ = ambiente
    monkeypatch.delitem(app.dependency_overrides, obter_usuario_atual)
    monkeypatch.setitem(app.dependency_overrides, get_limitador_login, lambda: Mock())
    senha = secrets.token_urlsafe(16)
    senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
    usuarios = [
        {
            "id": str(UUID(int=numero)), "nome": nome, "email": f"{nome}@example.com",
            "senha_hash": senha_hash, "telefone": None, "foto": None,
            "usuario_tipo": 0, "data_criacao": None,
        }
        for numero, nome in [(70, "ana-fluxo"), (71, "bia-fluxo")]
    ]
    banco.registros["usuario"].extend(usuarios)

    def entrar(usuario):
        resposta = cliente.post("/sessoes/login", json={
            "email": usuario["email"], "senha": senha,
        })
        assert resposta.status_code == 200
        return {"Authorization": f"Bearer {resposta.json()['token']}"}

    admin = entrar(usuarios[0])
    morador = entrar(usuarios[1])
    assert cliente.get("/casas/", headers=admin).json() == []
    assert cliente.get("/casas/", headers=morador).json() == []

    criacao = cliente.post("/casas/", headers=admin, json={
        "nome": "Casa compartilhada", "endereco": "Rua de teste, 10",
    })
    assert criacao.status_code == 201, criacao.text
    criada = criacao.json()
    casa_id = criada["id"]
    assert criada["fk_usuario_id"] == usuarios[0]["id"]
    assert cliente.get("/casas/", headers=admin).json() == [criada]
    assert cliente.get(f"/casas/{casa_id}", headers=morador).status_code == 403
    assert cliente.post(f"/casas/{casa_id}/convites", headers=morador).status_code == 403

    emissao = cliente.post(f"/casas/{casa_id}/convites", headers=admin)
    assert emissao.status_code == 200
    convite = emissao.json()["convite"]
    entrada = cliente.post("/casas/entrar", headers=morador, json={"convite": convite})
    assert entrada.status_code == 200
    assert entrada.json() == criada
    assert cliente.get("/casas/", headers=morador).json() == [criada]
    assert cliente.post(f"/casas/{casa_id}/convites", headers=morador).status_code == 403
    moradores = cliente.get(f"/casas/{casa_id}/moradores", headers=morador)
    assert moradores.status_code == 200
    assert {item["id"] for item in moradores.json()} == {item["id"] for item in usuarios}

    reentrada = cliente.post("/casas/entrar", headers=morador, json={"convite": convite})
    assert reentrada.status_code == 200
    assert len([
        item for item in banco.registros["pertencer"] if item["fk_casa_id"] == casa_id
    ]) == 2

    segunda = cliente.post("/casas/", headers=admin, json={
        "nome": "Outra casa", "endereco": "Rua de teste, 20",
    })
    assert segunda.status_code == 201
    assert {item["id"] for item in cliente.get("/casas/", headers=admin).json()} == {
        casa_id, segunda.json()["id"],
    }
    assert cliente.get("/casas/", headers=morador).json() == [criada]
    assert cliente.get(f"/casas/{segunda.json()['id']}", headers=morador).status_code == 403

    assert cliente.post("/sessoes/logout", headers=morador).status_code == 204
    assert cliente.get("/casas/", headers=morador).status_code == 401
    assert cliente.get("/casas/", headers=admin).status_code == 200
    nova_sessao = entrar(usuarios[1])
    assert cliente.get("/casas/", headers=nova_sessao).json() == [criada]


def test_listagem_filtra_antes_de_paginar_ordena_e_remove_duplicatas(ambiente):
    cliente, _, casas, _, _ = ambiente

    resposta = cliente.get("/casas/", params={"inicio": 1, "limite": 2})

    assert resposta.status_code == 200, resposta.text
    assert [item["id"] for item in resposta.json()] == [str(casas[2]), str(casas[4])]
    assert all(set(item) == {
        "id", "nome", "endereco", "foto", "fk_usuario_id", "timezone"
    } for item in resposta.json())


def test_listagem_omite_vinculo_inativo(ambiente):
    cliente, _, casas, _, _ = ambiente

    resposta = cliente.get("/casas/")

    assert resposta.status_code == 200, resposta.text
    assert [item["id"] for item in resposta.json()] == [
        str(casas[numero]) for numero in (1, 2, 4, 5)
    ]


@pytest.mark.parametrize("params", [
    {"inicio": -1}, {"limite": 0},
])
def test_paginacao_invalida_retorna_422(ambiente, params):
    cliente, _, _, _, _ = ambiente

    resposta = cliente.get("/casas/", params=params)

    assert resposta.status_code == 422, resposta.text


def test_listagem_sem_casas_retorna_200_e_lista_vazia(ambiente, monkeypatch):
    cliente, _, _, _, _ = ambiente
    trocar_usuario(monkeypatch, UUID(int=90))

    resposta = cliente.get("/casas/")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_leitura_da_casa_exige_propriedade_ou_vinculo(ambiente, monkeypatch):
    cliente, banco, casas, proprietario, _ = ambiente
    banco.registros["pertencer"] = [
        registro for registro in banco.registros["pertencer"]
        if registro["fk_casa_id"] != str(casas[1])
    ]
    assert not any(
        registro["fk_casa_id"] == str(casas[1])
        and registro["fk_usuario_id"] == str(proprietario)
        for registro in banco.registros["pertencer"]
    )

    assert cliente.get(f"/casas/{casas[1]}").status_code == 200
    assert cliente.get(f"/casas/{casas[2]}").status_code == 200
    assert cliente.get(f"/casas/{casas[3]}").status_code == 403
    assert cliente.get(f"/casas/{UUID(int=99)}").status_code == 404

    trocar_usuario(monkeypatch, UUID(int=90))
    assert cliente.get(f"/casas/{casas[1]}").status_code == 403


def test_moradores_mantem_score_e_requer_acesso(ambiente):
    cliente, _, casas, proprietario, _ = ambiente

    resposta = cliente.get(f"/casas/{casas[2]}/moradores")

    assert resposta.status_code == 200, resposta.text
    assert resposta.json() == [{
        "id": str(proprietario), "nome": "Ana", "email": "ana@example.com",
        "telefone": None, "foto": None, "score": 37,
    }]
    assert cliente.get(f"/casas/{casas[3]}/moradores").status_code == 403


def test_convite_so_pode_ser_emitido_pelo_proprietario(ambiente):
    cliente, _, casas, _, _ = ambiente

    resposta = cliente.post(f"/casas/{casas[1]}/convites")

    assert resposta.status_code == 200, resposta.text
    assert set(resposta.json()) == {"convite", "expira_em"}
    assert resposta.json()["convite"]
    expira_em = datetime.fromisoformat(resposta.json()["expira_em"].replace("Z", "+00:00"))
    restante = expira_em - datetime.now(timezone.utc)
    assert timedelta(hours=23, minutes=59) < restante <= timedelta(hours=24)
    assert cliente.post(f"/casas/{casas[2]}/convites").status_code == 403
    assert cliente.post(f"/casas/{UUID(int=99)}/convites").status_code == 404


def test_convite_vincula_usuario_da_sessao_e_reentrada_preserva_score(ambiente, monkeypatch):
    cliente, banco, casas, _, _ = ambiente
    convite = cliente.post(f"/casas/{casas[1]}/convites").json()["convite"]
    novo_morador = UUID(int=70)
    trocar_usuario(monkeypatch, novo_morador)

    primeira = cliente.post("/casas/entrar", json={"convite": convite})

    assert primeira.status_code == 200, primeira.text
    assert primeira.json()["id"] == str(casas[1])
    vinculados = [
        registro for registro in banco.registros["pertencer"]
        if registro["fk_casa_id"] == str(casas[1])
        and registro["fk_usuario_id"] == str(novo_morador)
    ]
    assert len(vinculados) == 1
    assert vinculados[0]["score"] == 0
    assert vinculados[0]["ativo"] is True
    vinculados[0]["score"] = 37

    segunda = cliente.post("/casas/entrar", json={"convite": convite})

    assert segunda.status_code == 200, segunda.text
    assert segunda.json() == primeira.json()
    assert len([
        registro for registro in banco.registros["pertencer"]
        if registro["fk_casa_id"] == str(casas[1])
        and registro["fk_usuario_id"] == str(novo_morador)
    ]) == 1
    assert vinculados[0]["score"] == 37


def test_reentrada_reativa_vinculo_e_preserva_score(ambiente, monkeypatch):
    cliente, banco, casas, _, _ = ambiente
    convite = cliente.post(f"/casas/{casas[1]}/convites").json()["convite"]
    antigo_morador = UUID(int=70)
    banco.registros["pertencer"].append(vinculo(casas[1], antigo_morador, 73, ativo=False))
    trocar_usuario(monkeypatch, antigo_morador)

    resposta = cliente.post("/casas/entrar", json={"convite": convite})

    assert resposta.status_code == 200, resposta.text
    registros = [
        item for item in banco.registros["pertencer"]
        if item["fk_casa_id"] == str(casas[1])
        and item["fk_usuario_id"] == str(antigo_morador)
    ]
    assert len(registros) == 1
    assert registros[0]["ativo"] is True
    assert registros[0]["score"] == 73


def test_convite_adulterado_e_payload_invalido_sao_rejeitados(ambiente):
    cliente, _, casas, _, _ = ambiente
    convite = cliente.post(f"/casas/{casas[1]}/convites").json()["convite"]
    adulterado = ("A" if convite[0] != "A" else "B") + convite[1:]

    assert cliente.post("/casas/entrar", json={"convite": adulterado}).status_code == 400
    assert cliente.post("/casas/entrar", json={"convite": "%%%._"}).status_code == 400
    assert cliente.post("/casas/entrar", json={}).status_code == 422
    assert cliente.post("/casas/entrar", json={"convite": 123}).status_code == 422


def test_convite_expirado_retorna_400(ambiente, monkeypatch):
    cliente, _, casas, _, _ = ambiente
    convite = cliente.post(f"/casas/{casas[1]}/convites").json()["convite"]

    class RelogioFuturo(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(timezone.utc) + timedelta(days=2)

    monkeypatch.setattr("services.convite_casa.datetime", RelogioFuturo)

    resposta = cliente.post("/casas/entrar", json={"convite": convite})

    assert resposta.status_code == 400, resposta.text


def test_convite_da_casa_removida_ou_com_novo_dono_nao_concede_acesso(
    ambiente, monkeypatch
):
    cliente, banco, casas, _, outro_proprietario = ambiente
    convite = cliente.post(f"/casas/{casas[1]}/convites").json()["convite"]
    trocar_usuario(monkeypatch, UUID(int=70))
    registro = next(
        casa for casa in banco.registros["casa"] if casa["id"] == str(casas[1])
    )
    registro["fk_usuario_id"] = str(outro_proprietario)

    assert cliente.post("/casas/entrar", json={"convite": convite}).status_code == 400
    banco.registros["casa"].remove(registro)
    assert cliente.post("/casas/entrar", json={"convite": convite}).status_code == 404
    assert not any(
        item["fk_casa_id"] == str(casas[1])
        and item["fk_usuario_id"] == str(UUID(int=70))
        for item in banco.registros["pertencer"]
    )


@pytest.mark.parametrize("segredo", [None, "fraco"])
def test_segredo_ausente_ou_fraco_indisponibiliza_rotas_de_convite(
    ambiente, monkeypatch, segredo
):
    cliente, _, casas, _, _ = ambiente
    convite = cliente.post(f"/casas/{casas[1]}/convites").json()["convite"]
    if segredo is None:
        monkeypatch.delenv("CASA_CONVITE_SECRET")
    else:
        monkeypatch.setenv("CASA_CONVITE_SECRET", segredo)

    assert cliente.post(f"/casas/{casas[1]}/convites").status_code == 503
    assert cliente.post("/casas/entrar", json={"convite": convite}).status_code == 503
    assert cliente.get(f"/casas/{casas[1]}").status_code == 200


def test_saida_inativa_so_vinculo_da_sessao_e_retorna_204(ambiente):
    cliente, banco, casas, proprietario, _ = ambiente
    vinculos_antes = deepcopy(banco.registros["pertencer"])

    resposta = cliente.delete(f"/casas/{casas[2]}/sair")

    assert resposta.status_code == 204, resposta.text
    assert resposta.content == b""
    assert len(banco.registros["pertencer"]) == len(vinculos_antes)
    alterados = [
        item for item in banco.registros["pertencer"]
        if item["fk_casa_id"] == str(casas[2])
        and item["fk_usuario_id"] == str(proprietario)
    ]
    assert len(alterados) == 1
    assert alterados[0]["ativo"] is False
    assert alterados[0]["score"] == 37
    assert cliente.get(f"/casas/{casas[2]}").status_code == 403
    assert cliente.delete(f"/casas/{casas[2]}/sair").status_code == 404


@pytest.mark.parametrize("bloqueio", ["proprietario", "tarefa_aberta"])
def test_saida_bloqueada_preserva_vinculo(ambiente, bloqueio):
    cliente, banco, casas, proprietario, _ = ambiente
    alvo = casas[1] if bloqueio == "proprietario" else casas[2]
    if bloqueio == "tarefa_aberta":
        tarefa_id = str(UUID(int=100))
        banco.registros["atribuida"].append({
            "fk_tarefa_id": tarefa_id, "fk_usuario_id": str(proprietario)
        })
        banco.registros["tarefa"].append({
            "id": tarefa_id, "fk_casa_id": str(alvo), "estado_atual": "pendente"
        })
    antes = deepcopy(banco.registros["pertencer"])

    resposta = cliente.delete(f"/casas/{alvo}/sair")

    assert resposta.status_code == 409, resposta.text
    assert banco.registros["pertencer"] == antes


def test_saida_com_historico_preserva_pontos_e_eventos(ambiente):
    cliente, banco, casas, proprietario, _ = ambiente
    evento = {"fk_casa_id": str(casas[2]), "fk_usuario_id": str(proprietario)}
    banco.registros["score_event"].append(evento)

    resposta = cliente.delete(f"/casas/{casas[2]}/sair")

    assert resposta.status_code == 204, resposta.text
    assert banco.registros["score_event"] == [evento]
    vinculado = next(
        item for item in banco.registros["pertencer"]
        if item["fk_casa_id"] == str(casas[2])
        and item["fk_usuario_id"] == str(proprietario)
    )
    assert vinculado["ativo"] is False
    assert vinculado["score"] == 37


def test_saida_sem_vinculo_ou_casa_retorna_404(ambiente):
    cliente, _, casas, _, _ = ambiente

    assert cliente.delete(f"/casas/{casas[3]}/sair").status_code == 404
    assert cliente.delete(f"/casas/{UUID(int=99)}/sair").status_code == 404


@pytest.mark.parametrize("metodo,caminho,corpo", [
    ("get", "/casas/", None),
    ("get", f"/casas/{UUID(int=1)}", None),
    ("post", f"/casas/{UUID(int=1)}/convites", None),
    ("post", "/casas/entrar", {"convite": "qualquer"}),
    ("delete", f"/casas/{UUID(int=1)}/sair", None),
])
def test_rotas_exigem_sessao(ambiente, monkeypatch, metodo, caminho, corpo):
    cliente, _, _, _, _ = ambiente
    monkeypatch.delitem(app.dependency_overrides, obter_usuario_atual)

    resposta = getattr(cliente, metodo)(caminho, json=corpo) if corpo else (
        getattr(cliente, metodo)(caminho)
    )

    assert resposta.status_code == 401, resposta.text


def test_uuid_invalido_retorna_422(ambiente):
    cliente, _, _, _, _ = ambiente

    assert cliente.get("/casas/uuid-invalido").status_code == 422
    assert cliente.post("/casas/uuid-invalido/convites").status_code == 422
    assert cliente.delete("/casas/uuid-invalido/sair").status_code == 422

def test_crud_mantem_proprietario_da_sessao_e_formato_de_resposta(ambiente):
    cliente, banco, _, proprietario, outro_proprietario = ambiente
    dados = {"nome": "Casa Nova", "endereco": "Rua Nova"}

    assert cliente.post("/casas/", json={
        **dados, "fk_usuario_id": str(outro_proprietario)
    }).status_code == 422
    criacao = cliente.post("/casas/", json=dados)

    assert criacao.status_code == 201, criacao.text
    criada = criacao.json()
    assert set(criada) == {
        "id", "nome", "endereco", "foto", "fk_usuario_id", "timezone"
    }
    assert criada["fk_usuario_id"] == str(proprietario)
    assert criada["nome"] == dados["nome"]
    assert criada["endereco"] == dados["endereco"]
    assert any(
        item["fk_casa_id"] == criada["id"]
        and item["fk_usuario_id"] == str(proprietario)
        for item in banco.registros["pertencer"]
    )

    assert cliente.patch(f"/casas/{criada['id']}", json={}).status_code == 400
    alteracao = cliente.patch(f"/casas/{criada['id']}", json={"nome": "Casa Nova 2"})
    assert alteracao.status_code == 200, alteracao.text
    assert alteracao.json() == {**criada, "nome": "Casa Nova 2"}
    exclusao = cliente.delete(f"/casas/{criada['id']}")
    assert exclusao.status_code == 200, exclusao.text
    assert exclusao.json() is True

ID_POR_CARGO = { "Morador":1, "Dono":2, "Forasteiro":3}

MATRIZ_CARGOS = [
    ("administrador", "get", "", None, 200),
    ("morador", "get", "", None, 200),
    ("forasteiro", "get", "", None, 403),
    ("administrador", "get", "/moradores", None, 200),
    ("morador", "get", "/moradores", None, 200),
    ("forasteiro", "get", "/moradores", None, 403),
    ("administrador", "patch", "", {"nome": "Alterada"}, 200),
    ("morador", "patch", "", {"nome": "Alterada"}, 403),
    ("forasteiro", "patch", "", {"nome": "Alterada"}, 403),
    ("administrador", "delete", "", None, 200),
    ("morador", "delete", "", None, 403),
    ("forasteiro", "delete", "", None, 403),
]

@pytest.Mark.parametrize( "cargo,metodo,sufixo,corpo,esperado",MATRIZ_CARGOS)
def test_operacoes_da_casa_por_cargo(ambiente, cargo, metodo, sufixo, 
corpo, esperado):
    cliente, banco, casas, _, _ = ambiente
    id_casa = casas[ID_POR_CARGO[cargo]]
    antes = deepcopy(banco.registros["casa"])

    resposta = getattr(cliente, metodo)(
        f"/casas/{id_casa}{sufixo}", **({"json": corpo} if corpo else {})
    )

    assert resposta.status_code == esperado, resposta.text
    if esperado == 403:
        assert banco.registros["casa"] == antes

def test_listagem_inclui_casas_de_administrador_e_morador_mas_nao_do_forasteiro(
    ambiente,
):
    cliente, _, casas, _, _ = ambiente

    ids = {item["id"] for item in cliente.get("/casas/").json()}

    assert {str(casas[1]), str(casas[2])} <= ids
    assert str(casas[3]) not in ids

