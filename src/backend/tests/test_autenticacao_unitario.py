import os
import secrets

import bcrypt
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from dotenv import load_dotenv


load_dotenv()
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_KEY", "unit-test-placeholder")

from core.autenticacao import UsuarioAtual  # noqa: E402
from core.database import get_supabase  # noqa: E402
from main import app as app_principal  # noqa: E402
from services.sessao import hash_token_sessao  # noqa: E402


class ConsultaFalsa:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
        self.filtros = []
        self.limite = None
        self.operacao = "select"
        self.novos_dados = None

    def insert(self, dados):
        self.operacao = "insert"
        self.novos_dados = dados
        return self

    def delete(self):
        self.operacao = "delete"
        return self

    def select(self, campos):
        self.banco.campos_selecionados.append((self.tabela, campos))
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor))
        return self

    def limit(self, limite):
        self.limite = limite
        return self

    def execute(self):
        if self.banco.erro is not None:
            raise self.banco.erro

        if self.operacao == "insert":
            registro = {"id": str(uuid4()), **self.novos_dados}
            self.banco.dados[self.tabela].append(registro)
            return SimpleNamespace(data=[registro])

        dados = list(self.banco.dados.get(self.tabela, []))
        for campo, valor in self.filtros:
            dados = [item for item in dados if str(item.get(campo)) == str(valor)]
        if self.limite is not None:
            dados = dados[: self.limite]
        if self.operacao == "delete":
            self.banco.dados[self.tabela] = [
                item for item in self.banco.dados[self.tabela] if item not in dados
            ]
        return SimpleNamespace(data=dados)


class BancoFalso:
    def __init__(self, sessoes=None, usuarios=None, erro=None):
        self.dados = {
            "sessao": sessoes or [],
            "usuario": usuarios or [],
        }
        self.erro = erro
        self.tabelas_consultadas = []
        self.campos_selecionados = []

    def table(self, tabela):
        self.tabelas_consultadas.append(tabela)
        return ConsultaFalsa(self, tabela)


app_teste = FastAPI()


@app_teste.get("/protegida")
def rota_protegida(usuario_atual: UsuarioAtual):
    return usuario_atual


@contextmanager
def cliente_com(banco):
    app_teste.dependency_overrides[get_supabase] = lambda: banco
    try:
        with TestClient(app_teste, raise_server_exceptions=False) as cliente:
            yield cliente
    finally:
        app_teste.dependency_overrides.clear()


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Basic credencial"},
        {"Authorization": "Bearer"},
    ],
)
def test_credencial_ausente_ou_incorreta_retorna_401(headers):
    banco = BancoFalso()

    with cliente_com(banco) as cliente:
        resposta = cliente.get("/protegida", headers=headers)

    assert resposta.status_code == 401
    assert resposta.headers["www-authenticate"] == "Bearer"
    assert banco.tabelas_consultadas == []


def test_token_invalido_retorna_401():
    banco = BancoFalso()

    with cliente_com(banco) as cliente:
        resposta = cliente.get(
            "/protegida",
            headers={"Authorization": "Bearer token-invalido"},
        )

    assert resposta.status_code == 401
    assert resposta.json() == {"detail": "Não autenticado."}
    assert banco.tabelas_consultadas == ["sessao"]


def test_token_expirado_retorna_401_sem_buscar_usuario():
    expiracao = (datetime.now(timezone.utc) - timedelta(minutes=1)).replace(
        tzinfo=None
    )
    banco = BancoFalso(
        sessoes=[
            {
                "token": hash_token_sessao("token-expirado"),
                "expira_em": expiracao.isoformat(),
                "fk_usuario_id": str(uuid4()),
            }
        ]
    )

    with cliente_com(banco) as cliente:
        resposta = cliente.get(
            "/protegida",
            headers={"Authorization": "Bearer token-expirado"},
        )

    assert resposta.status_code == 401
    assert banco.tabelas_consultadas == ["sessao"]


def test_expiracao_malformada_retorna_401_sem_buscar_usuario():
    banco = BancoFalso(
        sessoes=[
            {
                "token": hash_token_sessao("token-data-invalida"),
                "expira_em": "data-invalida",
                "fk_usuario_id": str(uuid4()),
            }
        ]
    )

    with cliente_com(banco) as cliente:
        resposta = cliente.get(
            "/protegida",
            headers={"Authorization": "Bearer token-data-invalida"},
        )

    assert resposta.status_code == 401
    assert banco.tabelas_consultadas == ["sessao"]


def test_token_duplicado_falha_de_forma_segura():
    usuario_id = str(uuid4())
    expiracao = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    sessao = {
        "token": hash_token_sessao("token-duplicado"),
        "expira_em": expiracao,
        "fk_usuario_id": usuario_id,
    }
    banco = BancoFalso(sessoes=[sessao, dict(sessao)])

    with cliente_com(banco) as cliente:
        resposta = cliente.get(
            "/protegida",
            headers={"Authorization": "Bearer token-duplicado"},
        )

    assert resposta.status_code == 401
    assert banco.tabelas_consultadas == ["sessao"]


def test_sessao_sem_usuario_retorna_401():
    usuario_id = str(uuid4())
    banco = BancoFalso(
        sessoes=[
            {
                "token": hash_token_sessao("token-orfao"),
                "expira_em": (
                    datetime.now(timezone.utc) + timedelta(hours=1)
                ).isoformat(),
                "fk_usuario_id": usuario_id,
            }
        ]
    )

    with cliente_com(banco) as cliente:
        resposta = cliente.get(
            "/protegida",
            headers={"Authorization": "Bearer token-orfao"},
        )

    assert resposta.status_code == 401
    assert banco.tabelas_consultadas == ["sessao", "usuario"]


def test_token_valido_disponibiliza_usuario_sem_senha_hash():
    usuario_id = str(uuid4())
    banco = BancoFalso(
        sessoes=[
            {
                "token": hash_token_sessao("token-valido"),
                "expira_em": (
                    datetime.now(timezone.utc) + timedelta(hours=1)
                ).isoformat().replace("+00:00", "Z"),
                "fk_usuario_id": usuario_id,
            }
        ],
        usuarios=[
            {
                "id": usuario_id,
                "nome": "Usuário autenticado",
                "email": "autenticado@example.com",
                "telefone": None,
                "foto": None,
                "usuario_tipo": 0,
                "data_criacao": None,
                "senha_hash": "nao-deve-ser-retornado",
            }
        ],
    )

    with cliente_com(banco) as cliente:
        resposta = cliente.get(
            "/protegida",
            headers={"Authorization": "Bearer token-valido"},
        )

    assert resposta.status_code == 200
    assert resposta.json()["id"] == usuario_id
    assert "senha_hash" not in resposta.json()
    assert banco.campos_selecionados == [
        ("sessao", "fk_usuario_id,expira_em"),
        ("usuario", "id,nome,email,telefone,foto,usuario_tipo,data_criacao"),
    ]


def test_falha_do_banco_nao_e_convertida_em_401():
    banco = BancoFalso(erro=RuntimeError("falha simulada"))

    with cliente_com(banco) as cliente:
        resposta = cliente.get(
            "/protegida",
            headers={"Authorization": "Bearer token"},
        )

    assert resposta.status_code == 500


@pytest.mark.parametrize(
    "caminho",
    [
        "/usuarios/",
        "/casas/",
        "/tarefas/",
        "/pertencer/",
    ],
)
def test_rotas_protegidas_rejeitam_requisicao_sem_token(caminho):
    with TestClient(app_principal, raise_server_exceptions=False) as cliente:
        resposta = cliente.get(caminho)

    assert resposta.status_code == 401
    assert resposta.headers["www-authenticate"] == "Bearer"


def test_health_e_cadastro_continuam_publicos():
    with TestClient(app_principal, raise_server_exceptions=False) as cliente:
        health = cliente.get("/health")
        cadastro_invalido = cliente.post("/usuarios/", json={})

    assert health.status_code == 200
    assert cadastro_invalido.status_code == 422

@pytest.fixture
def banco_login():
    senha = secrets.token_urlsafe(24)
    banco = BancoFalso(usuarios=[{
        "id": str(uuid4()), "nome": "Morador", "email": "morador@example.com",
        "senha_hash": bcrypt.hashpw(senha.encode(), bcrypt.gensalt(rounds=4)).decode(),
    }])
    return banco, {"email": "morador@example.com", "senha": senha}


@contextmanager
def cliente_principal(banco):
    app_principal.dependency_overrides[get_supabase] = lambda: banco
    try:
        with TestClient(app_principal, raise_server_exceptions=False) as cliente:
            yield cliente
    finally:
        app_principal.dependency_overrides.clear()


def test_login_acessa_rota_protegida_e_logout_preserva_outra_sessao(banco_login):
    banco, credenciais = banco_login
    with cliente_principal(banco) as cliente:
        login = cliente.post("/sessoes/login", json=credenciais)
        outro_login = cliente.post("/sessoes/login", json=credenciais)
        assert login.status_code == outro_login.status_code == 200
        assert login.headers["cache-control"] == "no-store"
        token = login.json()["token"]
        outro_token = outro_login.json()["token"]
        assert token != outro_token
        assert set(login.json()) == {"token", "expira_em"}
        headers = {"Authorization": f"Bearer {token}"}
        eu = cliente.get("/usuarios/eu", headers=headers)
        assert eu.status_code == 200
        assert eu.json()["id"] == banco.dados["usuario"][0]["id"]
        assert "senha_hash" not in eu.json()

        logout = cliente.post("/sessoes/logout", headers=headers)
        assert logout.status_code == 204
        assert logout.content == b""
        assert cliente.get("/usuarios/eu", headers=headers).status_code == 401
        assert cliente.get(
            "/usuarios/eu", headers={"Authorization": f"Bearer {outro_token}"}
        ).status_code == 200
        assert len(banco.dados["sessao"]) == 1


def test_hash_armazenado_e_token_legado_nao_autenticam(banco_login):
    banco, credenciais = banco_login
    legado = secrets.token_urlsafe(32)
    banco.dados["sessao"].append({
        "token": legado, "fk_usuario_id": banco.dados["usuario"][0]["id"],
        "expira_em": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    })
    with cliente_principal(banco) as cliente:
        assert cliente.post("/sessoes/login", json=credenciais).status_code == 200
        for token in [legado, banco.dados["sessao"][-1]["token"]]:
            resposta = cliente.get(
                "/usuarios/eu", headers={"Authorization": f"Bearer {token}"}
            )
            assert resposta.status_code == 401


@pytest.mark.parametrize("metodo,caminho", [
    ("GET", "/sessoes/"), ("POST", "/sessoes/"),
    ("GET", "/sessoes/{id}"), ("PATCH", "/sessoes/{id}"),
    ("DELETE", "/sessoes/{id}"),
])
@pytest.mark.parametrize("autenticado", [False, True])
def test_crud_de_sessoes_foi_removido(banco_login, metodo, caminho, autenticado):
    banco, credenciais = banco_login
    with cliente_principal(banco) as cliente:
        headers = {}
        if autenticado:
            login = cliente.post("/sessoes/login", json=credenciais)
            headers["Authorization"] = f"Bearer {login.json()['token']}"
        resposta = cliente.request(
            metodo, caminho.replace("{id}", str(uuid4())), headers=headers
        )
    assert resposta.status_code == 404


def test_logout_sem_token_nao_remove_sessoes(banco_login):
    banco, _ = banco_login
    with cliente_principal(banco) as cliente:
        resposta = cliente.post("/sessoes/logout")
    assert resposta.status_code == 401
    assert banco.tabelas_consultadas == []


@pytest.mark.parametrize("extra", ["fk_usuario_id", "token", "expira_em"])
def test_login_rejeita_campos_controlados_pelo_servidor(banco_login, extra):
    banco, credenciais = banco_login
    with cliente_principal(banco) as cliente:
        resposta = cliente.post("/sessoes/login", json={**credenciais, extra: str(uuid4())})
    assert resposta.status_code == 422
    assert banco.dados["sessao"] == []


def test_openapi_publica_login_logout_e_pertencer_sem_crud_sessao():
    caminhos = app_principal.openapi()["paths"]
    assert "/sessoes/" not in caminhos
    assert "/sessoes/{id_sessao}" not in caminhos
    assert not caminhos["/sessoes/login"]["post"].get("security")
    assert caminhos["/sessoes/logout"]["post"]["security"]
    assert {"get", "post"} <= caminhos["/pertencer/"].keys()
    assert {"get", "delete"} <= caminhos["/pertencer/{fk_usuario_id}/{fk_casa_id}"].keys()
