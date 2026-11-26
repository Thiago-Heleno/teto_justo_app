"""Testes unitários de regras da casa e multas com banco em memória."""

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
        self.contidos = []
        self.intervalo = None
        self.ordens = []
        self.limite = None
        self.dados = None

    def select(self, campos):
        self.campos = campos
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor))
        return self

    def in_(self, campo, valores):
        self.contidos.append((campo, [str(valor) for valor in valores]))
        return self

    def range(self, inicio, fim):
        self.intervalo = (inicio, fim + 1)
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
        return all(str(registro.get(c)) == str(v) for c, v in self.filtros) and all(
            str(registro.get(c)) in v for c, v in self.contidos
        )

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
                if self.tabela == "regra_casa":
                    registro.setdefault("ativa", True)
                if self.tabela == "multa_casa":
                    registro.setdefault("paga", False)
                    registro.setdefault("pago_em", None)
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
        if self.intervalo is not None:
            selecionados = selecionados[slice(*self.intervalo)]
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
def cenario():
    admin_id, morador_id, inativo_id, forasteiro_id = uuid4(), uuid4(), uuid4(), uuid4()
    casa_id, outra_casa_id = uuid4(), uuid4()
    regra_id, regra_inativa_id, regra_outra_casa_id = uuid4(), uuid4(), uuid4()

    def regra(id_, casa, titulo, valor, ativa=True):
        return {
            "id": str(id_),
            "fk_casa_id": str(casa),
            "titulo": titulo,
            "descricao": None,
            "valor_multa_centavos": valor,
            "ativa": ativa,
            "criado_em": "2026-11-01T10:00:00+00:00",
        }

    banco = SupabaseEmMemoria(
        {
            "casa": [
                {"id": str(casa_id), "fk_usuario_id": str(admin_id)},
                {"id": str(outra_casa_id), "fk_usuario_id": str(forasteiro_id)},
            ],
            "pertencer": [
                {"fk_casa_id": str(casa_id), "fk_usuario_id": str(morador_id), "ativo": True},
                {"fk_casa_id": str(casa_id), "fk_usuario_id": str(inativo_id), "ativo": False},
            ],
            "regra_casa": [
                regra(regra_id, casa_id, "Louça na pia", 1500),
                regra(regra_inativa_id, casa_id, "Regra antiga", 500, ativa=False),
                regra(regra_outra_casa_id, outra_casa_id, "Outra casa", 700),
            ],
            "multa_casa": [],
        }
    )
    usuario_atual = {"id": admin_id}
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
                regra_id=regra_id,
                regra_inativa_id=regra_inativa_id,
                regra_outra_casa_id=regra_outra_casa_id,
            )
    finally:
        app.dependency_overrides.pop(get_supabase, None)
        app.dependency_overrides.pop(obter_usuario_atual, None)


def test_admin_cria_regra_com_descricao_vazia_virando_nula(cenario):
    r = cenario.cliente.post(
        "/regras-casa/",
        json={
            "fk_casa_id": str(cenario.casa_id),
            "titulo": "  Barulho  ",
            "descricao": "   ",
            "valor_multa_centavos": 2000,
        },
    )
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["titulo"] == "Barulho"
    assert corpo["descricao"] is None
    assert corpo["ativa"] is True
    assert corpo["valor_multa_centavos"] == 2000


@pytest.mark.parametrize("valor", [0, -1, 2147483648])
def test_valor_da_multa_fora_do_limite_e_rejeitado(cenario, valor):
    r = cenario.cliente.post(
        "/regras-casa/",
        json={"fk_casa_id": str(cenario.casa_id), "titulo": "X", "valor_multa_centavos": valor},
    )
    assert r.status_code == 422


def test_morador_nao_cria_atualiza_nem_exclui_regra(cenario):
    cenario.usuario_atual["id"] = cenario.morador_id
    criar = cenario.cliente.post(
        "/regras-casa/",
        json={"fk_casa_id": str(cenario.casa_id), "titulo": "X", "valor_multa_centavos": 100},
    )
    atualizar = cenario.cliente.patch(f"/regras-casa/{cenario.regra_id}", json={"ativa": False})
    excluir = cenario.cliente.delete(f"/regras-casa/{cenario.regra_id}")
    assert [criar.status_code, atualizar.status_code, excluir.status_code] == [403, 403, 403]


def test_morador_ativo_lista_regras_e_forasteiro_ou_inativo_nao(cenario):
    cenario.usuario_atual["id"] = cenario.morador_id
    r = cenario.cliente.get(f"/regras-casa/casa/{cenario.casa_id}")
    assert r.status_code == 200
    assert {x["titulo"] for x in r.json()} == {"Louça na pia", "Regra antiga"}
    for intruso in (cenario.forasteiro_id, cenario.inativo_id):
        cenario.usuario_atual["id"] = intruso
        assert cenario.cliente.get(f"/regras-casa/casa/{cenario.casa_id}").status_code == 403


def test_admin_atualiza_regra_e_limpa_descricao(cenario):
    r = cenario.cliente.patch(
        f"/regras-casa/{cenario.regra_id}",
        json={"descricao": "x", "valor_multa_centavos": 900, "ativa": False},
    )
    assert r.status_code == 200
    assert (r.json()["descricao"], r.json()["valor_multa_centavos"], r.json()["ativa"]) == (
        "x",
        900,
        False,
    )
    r = cenario.cliente.patch(f"/regras-casa/{cenario.regra_id}", json={"descricao": ""})
    assert r.json()["descricao"] is None


def test_atualizar_regra_sem_campos_retorna_422(cenario):
    assert cenario.cliente.patch(f"/regras-casa/{cenario.regra_id}", json={}).status_code == 422


def test_admin_exclui_regra_e_regra_inexistente_retorna_404(cenario):
    assert cenario.cliente.delete(f"/regras-casa/{cenario.regra_id}").status_code == 204
    assert cenario.cliente.delete(f"/regras-casa/{cenario.regra_id}").status_code == 404


def _aplicar_multa(c, **extra):
    corpo = {
        "fk_casa_id": str(c.casa_id),
        "fk_regra_id": str(c.regra_id),
        "fk_usuario_multado_id": str(c.morador_id),
    } | extra
    return c.cliente.post("/regras-casa/multas", json=corpo)


def test_multa_copia_titulo_e_valor_da_regra_e_registra_aplicador(cenario):
    r = _aplicar_multa(cenario, observacao="  de novo  ")
    assert r.status_code == 201
    multa = r.json()
    assert multa["titulo_regra"] == "Louça na pia"
    assert multa["valor_centavos"] == 1500
    assert multa["fk_usuario_aplicador_id"] == str(cenario.admin_id)
    assert multa["observacao"] == "de novo"
    assert multa["paga"] is False and multa["pago_em"] is None
    cenario.banco.registros["regra_casa"][0]["valor_multa_centavos"] = 9999
    listadas = cenario.cliente.get(f"/regras-casa/casa/{cenario.casa_id}/multas").json()
    assert listadas[0]["valor_centavos"] == 1500


def test_multa_rejeita_regra_inativa_regra_de_outra_casa_e_multado_estranho(cenario):
    inativa = _aplicar_multa(cenario, fk_regra_id=str(cenario.regra_inativa_id))
    outra = _aplicar_multa(cenario, fk_regra_id=str(cenario.regra_outra_casa_id))
    forasteiro = _aplicar_multa(cenario, fk_usuario_multado_id=str(cenario.forasteiro_id))
    inativo = _aplicar_multa(cenario, fk_usuario_multado_id=str(cenario.inativo_id))
    assert [r.status_code for r in (inativa, outra, forasteiro, inativo)] == [422] * 4


def test_multa_regra_inexistente_retorna_404(cenario):
    assert _aplicar_multa(cenario, fk_regra_id=str(uuid4())).status_code == 404


def test_admin_marca_e_desmarca_multa_como_paga(cenario):
    multa_id = _aplicar_multa(cenario).json()["id"]
    paga = cenario.cliente.post(f"/regras-casa/multas/{multa_id}/pagar")
    assert paga.status_code == 200
    assert paga.json()["paga"] is True and paga.json()["pago_em"] is not None
    desfeita = cenario.cliente.delete(f"/regras-casa/multas/{multa_id}/pagar")
    assert desfeita.json()["paga"] is False and desfeita.json()["pago_em"] is None


def test_morador_lista_multas_mas_nao_aplica_paga_nem_exclui(cenario):
    multa_id = _aplicar_multa(cenario).json()["id"]
    cenario.usuario_atual["id"] = cenario.morador_id
    assert len(cenario.cliente.get(f"/regras-casa/casa/{cenario.casa_id}/multas").json()) == 1
    resultados = [
        _aplicar_multa(cenario).status_code,
        cenario.cliente.post(f"/regras-casa/multas/{multa_id}/pagar").status_code,
        cenario.cliente.delete(f"/regras-casa/multas/{multa_id}/pagar").status_code,
        cenario.cliente.delete(f"/regras-casa/multas/{multa_id}").status_code,
    ]
    assert resultados == [403, 403, 403, 403]


def test_admin_exclui_multa(cenario):
    multa_id = _aplicar_multa(cenario).json()["id"]
    assert cenario.cliente.delete(f"/regras-casa/multas/{multa_id}").status_code == 204
    assert cenario.cliente.get(f"/regras-casa/casa/{cenario.casa_id}/multas").json() == []


def test_regra_com_multa_nao_pode_ser_excluida(cenario):
    _aplicar_multa(cenario)
    assert cenario.cliente.delete(f"/regras-casa/{cenario.regra_id}").status_code == 409
    assert len(cenario.banco.registros["multa_casa"]) == 1
