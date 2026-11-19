"""Testes unitários do router e serviço de lista de compras com banco em memória."""

import os
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
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


class ConsultaEmMemoria:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
        self.acao = "select"
        self.campos = "*"
        self.filtros = []
        self.ordens = []
        self.limite = None
        self.dados = None

    def select(self, campos):
        self.campos = campos
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor))
        return self

    def order(self, campo, desc=False):
        self.ordens.append((campo, desc))
        return self

    def limit(self, quantidade):
        self.limite = quantidade
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
        return all(str(registro.get(campo)) == str(valor) for campo, valor in self.filtros)

    def execute(self):
        registros = self.banco.registros.setdefault(self.tabela, [])
        selecionados = [registro for registro in registros if self._corresponde(registro)]

        if self.acao == "insert":
            novos = self.dados if isinstance(self.dados, list) else [self.dados]
            criados = []
            for novo in novos:
                registro = deepcopy(novo)
                registro.setdefault("id", str(uuid4()))
                registro.setdefault("criado_em", datetime.now(timezone.utc).isoformat())
                if self.tabela == "item_compra":
                    registro.setdefault("comprado", False)
                    registro.setdefault("fk_usuario_comprador_id", None)
                    registro.setdefault("comprado_em", None)
                registros.append(registro)
                criados.append(registro)
            return SimpleNamespace(data=deepcopy(criados))

        if self.acao == "update":
            for registro in selecionados:
                registro.update(deepcopy(self.dados))
            return SimpleNamespace(data=deepcopy(selecionados))

        if self.acao == "delete":
            for registro in selecionados:
                registros.remove(registro)
            return SimpleNamespace(data=deepcopy(selecionados))

        for campo, decrescente in reversed(self.ordens):
            selecionados.sort(key=lambda r: str(r.get(campo, "")), reverse=decrescente)
        if self.limite is not None:
            selecionados = selecionados[: self.limite]
        if self.campos != "*":
            nomes = [campo.strip() for campo in self.campos.split(",")]
            selecionados = [{campo: r.get(campo) for campo in nomes} for r in selecionados]
        return SimpleNamespace(data=deepcopy(selecionados))


class SupabaseEmMemoria:
    def __init__(self, registros):
        self.registros = registros

    def table(self, tabela):
        return ConsultaEmMemoria(self, tabela)


def _usuario_fake(usuario_id: UUID):
    return SimpleNamespace(id=usuario_id)


@pytest.fixture
def cenario_lista():
    admin_id = uuid4()
    morador_id = uuid4()
    inativo_id = uuid4()
    forasteiro_id = uuid4()
    casa_id = uuid4()
    outra_casa_id = uuid4()
    lista_id = uuid4()
    outra_lista_id = uuid4()
    item_id = uuid4()

    banco = SupabaseEmMemoria(
        {
            "casa": [
                {"id": str(casa_id), "fk_usuario_id": str(admin_id)},
                {"id": str(outra_casa_id), "fk_usuario_id": str(forasteiro_id)},
            ],
            "pertencer": [
                {"fk_casa_id": str(casa_id), "fk_usuario_id": str(admin_id), "ativo": True},
                {"fk_casa_id": str(casa_id), "fk_usuario_id": str(morador_id), "ativo": True},
                {"fk_casa_id": str(casa_id), "fk_usuario_id": str(inativo_id), "ativo": False},
            ],
            "lista_compra": [
                {
                    "id": str(lista_id),
                    "fk_casa_id": str(casa_id),
                    "nome": "Mercado",
                    "criado_em": "2026-10-01T10:00:00+00:00",
                },
                {
                    "id": str(outra_lista_id),
                    "fk_casa_id": str(outra_casa_id),
                    "nome": "Outra casa",
                    "criado_em": "2026-10-01T11:00:00+00:00",
                },
            ],
            "item_compra": [
                {
                    "id": str(item_id),
                    "fk_lista_id": str(lista_id),
                    "nome": "Arroz",
                    "quantidade": 2,
                    "fk_usuario_criador_id": str(admin_id),
                    "comprado": False,
                    "fk_usuario_comprador_id": None,
                    "comprado_em": None,
                    "criado_em": "2026-10-01T10:05:00+00:00",
                }
            ],
        }
    )
    usuario_atual = {"id": morador_id}
    app.dependency_overrides[get_supabase] = lambda: banco
    app.dependency_overrides[obter_usuario_atual] = lambda: _usuario_fake(usuario_atual["id"])

    try:
        with TestClient(app) as cliente:
            yield SimpleNamespace(
                cliente=cliente,
                banco=banco,
                usuario_atual=usuario_atual,
                admin_id=admin_id,
                morador_id=morador_id,
                inativo_id=inativo_id,
                forasteiro_id=forasteiro_id,
                casa_id=casa_id,
                lista_id=lista_id,
                item_id=item_id,
            )
    finally:
        app.dependency_overrides.pop(get_supabase, None)
        app.dependency_overrides.pop(obter_usuario_atual, None)


def test_morador_ativo_e_admin_criam_e_listam_listas_da_casa(cenario_lista):
    criada = cenario_lista.cliente.post(
        "/lista/",
        json={"nome": "  Limpeza  ", "fk_casa_id": str(cenario_lista.casa_id)},
    )
    assert criada.status_code == 201
    assert criada.json()["nome"] == "Limpeza"
    assert criada.json()["fk_casa_id"] == str(cenario_lista.casa_id)

    cenario_lista.usuario_atual["id"] = cenario_lista.admin_id
    listas = cenario_lista.cliente.get(f"/lista/casa/{cenario_lista.casa_id}")
    assert listas.status_code == 200
    assert [item["nome"] for item in listas.json()] == ["Mercado", "Limpeza"]


@pytest.mark.parametrize("papel", ["forasteiro_id", "inativo_id"])
def test_forasteiro_e_morador_inativo_recebem_403_nas_operacoes_de_lista(cenario_lista, papel):
    cenario_lista.usuario_atual["id"] = getattr(cenario_lista, papel)

    assert (
        cenario_lista.cliente.post(
            "/lista/",
            json={"nome": "Invasão", "fk_casa_id": str(cenario_lista.casa_id)},
        ).status_code
        == 403
    )
    assert cenario_lista.cliente.get(f"/lista/casa/{cenario_lista.casa_id}").status_code == 403
    assert (
        cenario_lista.cliente.patch(
            f"/lista/{cenario_lista.lista_id}",
            json={"nome": "Alterada"},
        ).status_code
        == 403
    )
    assert cenario_lista.cliente.delete(f"/lista/{cenario_lista.lista_id}").status_code == 403


def test_atualizar_e_deletar_lista_respeitam_existencia_e_cargo(cenario_lista):
    renomeada = cenario_lista.cliente.patch(
        f"/lista/{cenario_lista.lista_id}",
        json={"nome": "  Feira  "},
    )
    assert renomeada.status_code == 200
    assert renomeada.json()["nome"] == "Feira"

    negada_morador = cenario_lista.cliente.delete(f"/lista/{cenario_lista.lista_id}")
    assert negada_morador.status_code == 403
    assert any(
        r["id"] == str(cenario_lista.lista_id)
        for r in cenario_lista.banco.registros["lista_compra"]
    )

    cenario_lista.usuario_atual["id"] = cenario_lista.admin_id
    excluida = cenario_lista.cliente.delete(f"/lista/{cenario_lista.lista_id}")
    assert excluida.status_code == 204
    assert excluida.content == b""
    assert all(
        r["id"] != str(cenario_lista.lista_id)
        for r in cenario_lista.banco.registros["lista_compra"]
    )

    inexistente = cenario_lista.cliente.patch(
        f"/lista/{uuid4()}",
        json={"nome": "Fantasma"},
    )
    assert inexistente.status_code == 404


def test_criar_e_listar_itens_grava_criador_autenticado_e_rejeita_payload_invalido(cenario_lista):
    criado = cenario_lista.cliente.post(
        "/lista/itens",
        json={"nome": "  Detergente  ", "fk_lista_id": str(cenario_lista.lista_id)},
    )
    assert criado.status_code == 201
    corpo = criado.json()
    assert corpo["nome"] == "Detergente"
    assert corpo["quantidade"] == 1
    assert corpo["fk_usuario_criador_id"] == str(cenario_lista.morador_id)
    assert corpo["comprado"] is False

    invalido_qtd = cenario_lista.cliente.post(
        "/lista/itens",
        json={"nome": "Sabão", "quantidade": 0, "fk_lista_id": str(cenario_lista.lista_id)},
    )
    assert invalido_qtd.status_code == 422

    invalido_extra = cenario_lista.cliente.post(
        "/lista/itens",
        json={
            "nome": "Sabão",
            "fk_lista_id": str(cenario_lista.lista_id),
            "fk_usuario_criador_id": str(cenario_lista.admin_id),
        },
    )
    assert invalido_extra.status_code == 422

    itens = cenario_lista.cliente.get(f"/lista/{cenario_lista.lista_id}/itens")
    assert itens.status_code == 200
    assert [item["nome"] for item in itens.json()] == ["Arroz", "Detergente"]

    cenario_lista.usuario_atual["id"] = cenario_lista.forasteiro_id
    assert cenario_lista.cliente.get(f"/lista/{cenario_lista.lista_id}/itens").status_code == 403


def test_atualizar_item_rejeita_vazio_ou_nulo_e_atualiza_campos_informados(cenario_lista):
    vazio = cenario_lista.cliente.patch(f"/lista/itens/{cenario_lista.item_id}", json={})
    assert vazio.status_code == 422

    nulo = cenario_lista.cliente.patch(
        f"/lista/itens/{cenario_lista.item_id}",
        json={"nome": None},
    )
    assert nulo.status_code == 422

    atualizado = cenario_lista.cliente.patch(
        f"/lista/itens/{cenario_lista.item_id}",
        json={"nome": "  Arroz integral  ", "quantidade": 3},
    )
    assert atualizado.status_code == 200
    assert atualizado.json()["nome"] == "Arroz integral"
    assert atualizado.json()["quantidade"] == 3


def test_marcar_e_desmarcar_comprado_preenche_e_limpa_comprador_e_instante(cenario_lista):
    marcado = cenario_lista.cliente.post(f"/lista/itens/{cenario_lista.item_id}/comprado")
    assert marcado.status_code == 200
    assert marcado.json()["comprado"] is True
    assert marcado.json()["fk_usuario_comprador_id"] == str(cenario_lista.morador_id)
    assert marcado.json()["comprado_em"] is not None

    cenario_lista.usuario_atual["id"] = cenario_lista.admin_id
    desmarcado = cenario_lista.cliente.delete(f"/lista/itens/{cenario_lista.item_id}/comprado")
    assert desmarcado.status_code == 200
    assert desmarcado.json()["comprado"] is False
    assert desmarcado.json()["fk_usuario_comprador_id"] is None
    assert desmarcado.json()["comprado_em"] is None


def test_deletar_item_permite_morador_e_nega_forasteiro(cenario_lista):
    cenario_lista.usuario_atual["id"] = cenario_lista.forasteiro_id
    negado = cenario_lista.cliente.delete(f"/lista/itens/{cenario_lista.item_id}")
    assert negado.status_code == 403

    cenario_lista.usuario_atual["id"] = cenario_lista.morador_id
    excluido = cenario_lista.cliente.delete(f"/lista/itens/{cenario_lista.item_id}")
    assert excluido.status_code == 204
    assert excluido.content == b""

    inexistente = cenario_lista.cliente.delete(f"/lista/itens/{cenario_lista.item_id}")
    assert inexistente.status_code == 404
