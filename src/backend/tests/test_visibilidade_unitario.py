import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_KEY", "unit-test-placeholder")

from core.autenticacao import obter_usuario_atual  # noqa: E402
from core.database import get_supabase  # noqa: E402
from main import app  # noqa: E402
from schemas.usuario import UsuarioResposta  # noqa: E402


class ConsultaEmMemoria:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
        self.campos = "*"
        self.filtros = []
        self.lotes = []
        self.ordens = []
        self.inicio = 0
        self.fim = None

    def select(self, campos):
        self.campos = campos
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, str(valor)))
        return self

    def in_(self, campo, valores):
        self.lotes.append((campo, {str(valor) for valor in valores}))
        return self

    def order(self, campo):
        self.ordens.append(campo)
        return self

    def range(self, inicio, fim):
        self.inicio, self.fim = inicio, fim
        return self

    def limit(self, limite):
        self.fim = limite - 1
        return self

    def execute(self):
        self.banco.consultas.append(self.tabela)
        encontrados = [
            registro for registro in self.banco.dados[self.tabela]
            if all(str(registro.get(campo)) == valor for campo, valor in self.filtros)
            and all(str(registro.get(campo)) in valores for campo, valores in self.lotes)
        ]
        for campo in reversed(self.ordens):
            encontrados.sort(key=lambda registro: str(registro.get(campo)))
        if self.fim is not None:
            encontrados = encontrados[self.inicio:self.fim + 1]
        campos = self.campos.split(",") if self.campos != "*" else None
        return SimpleNamespace(data=[
            {campo: registro[campo] for campo in campos} if campos else dict(registro)
            for registro in encontrados
        ])


class BancoEmMemoria:
    def __init__(self, dados):
        self.dados = dados
        self.consultas = []

    def table(self, tabela):
        return ConsultaEmMemoria(self, tabela)


def _cenario():
    ids = {nome: str(uuid4()) for nome in (
        "atual", "dono_compartilhada", "outro", "ex_morador",
        "casa_propria", "casa_compartilhada", "casa_alheia", "casa_saida",
        "tarefa_propria", "tarefa_compartilhada", "tarefa_alheia", "tarefa_saida",
    )}
    usuarios = [
        {"id": ids[nome], "nome": nome, "email": f"{nome}@example.com",
         "telefone": None, "foto": None, "usuario_tipo": 0, "data_criacao": None}
        for nome in ("atual", "dono_compartilhada", "outro", "ex_morador")
    ]
    casas = [
        {"id": ids[casa], "fk_usuario_id": ids[dono]}
        for casa, dono in (
            ("casa_propria", "atual"),
            ("casa_compartilhada", "dono_compartilhada"),
            ("casa_alheia", "outro"),
            ("casa_saida", "ex_morador"),
        )
    ]
    vinculos = [
        {"fk_casa_id": ids["casa_compartilhada"],
         "fk_usuario_id": ids["atual"], "ativo": True, "score": 0},
        {"fk_casa_id": ids["casa_compartilhada"],
         "fk_usuario_id": ids["dono_compartilhada"], "ativo": True, "score": 0},
        {"fk_casa_id": ids["casa_alheia"],
         "fk_usuario_id": ids["outro"], "ativo": True, "score": 0},
        {"fk_casa_id": ids["casa_saida"],
         "fk_usuario_id": ids["atual"], "ativo": False, "score": 0},
    ]
    prazo = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    tarefas = [
        {"id": ids[tarefa], "nome": tarefa, "fk_casa_id": ids[casa],
         "fk_usuario_id": ids[dono], "estado_atual": "pendente",
         "dificuldade": 1, "atraso_maximo": 1, "data_fim": prazo,
         "modo_prazo": "intervalo", "tipo": "unitaria"}
        for tarefa, casa, dono in (
            ("tarefa_propria", "casa_propria", "atual"),
            ("tarefa_compartilhada", "casa_compartilhada", "dono_compartilhada"),
            ("tarefa_alheia", "casa_alheia", "outro"),
            ("tarefa_saida", "casa_saida", "ex_morador"),
        )
    ]
    banco = BancoEmMemoria({
        "usuario": usuarios, "casa": casas, "pertencer": vinculos,
        "tarefa": tarefas, "atribuida": [],
    })
    return ids, banco, UsuarioResposta.model_validate(usuarios[0])


def test_tarefas_e_vinculos_filtrados_antes_da_paginacao():
    ids, banco, atual = _cenario()
    app.dependency_overrides[get_supabase] = lambda: banco
    app.dependency_overrides[obter_usuario_atual] = lambda: atual
    try:
        with TestClient(app) as cliente:
            tarefas = cliente.get("/tarefas/")
            assert tarefas.status_code == 200, tarefas.text
            ids_visiveis = {tarefa["id"] for tarefa in tarefas.json()}
            assert ids_visiveis == {ids["tarefa_propria"], ids["tarefa_compartilhada"]}
            pagina = cliente.get("/tarefas/?inicio=1&limite=1")
            assert [t["id"] for t in pagina.json()] == sorted(ids_visiveis)[1:2]

            vinculos = cliente.get("/pertencer/")
            assert vinculos.status_code == 200, vinculos.text
            assert {v["fk_casa_id"] for v in vinculos.json()} == {ids["casa_compartilhada"]}
            assert len(cliente.get("/pertencer/?inicio=1&limite=1").json()) == 1
    finally:
        app.dependency_overrides.clear()


def test_consultas_por_id_negam_casa_alheia_e_ex_morador_antes_de_montar_tarefa():
    ids, banco, atual = _cenario()
    app.dependency_overrides[get_supabase] = lambda: banco
    app.dependency_overrides[obter_usuario_atual] = lambda: atual
    try:
        with TestClient(app) as cliente:
            for casa in ("casa_alheia", "casa_saida"):
                assert cliente.get(f"/tarefas/casa/{ids[casa]}").status_code == 403
                assert cliente.get(f"/pertencer/{ids['atual']}/{ids[casa]}").status_code == 403
            for tarefa in ("tarefa_alheia", "tarefa_saida"):
                banco.consultas.clear()
                assert cliente.get(f"/tarefas/{ids[tarefa]}").status_code == 403
                assert "atribuida" not in banco.consultas
            assert cliente.get(f"/tarefas/{ids['tarefa_propria']}").status_code == 200
            assert cliente.get(f"/tarefas/{ids['tarefa_compartilhada']}").status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_perfis_apenas_da_mesma_casa_e_alteracoes_apenas_da_propria_conta():
    ids, banco, atual = _cenario()
    app.dependency_overrides[get_supabase] = lambda: banco
    app.dependency_overrides[obter_usuario_atual] = lambda: atual
    try:
        with TestClient(app) as cliente:
            lista = cliente.get("/usuarios/")
            assert lista.status_code == 200, lista.text
            assert {usuario["id"] for usuario in lista.json()} == {
                ids["atual"], ids["dono_compartilhada"]
            }
            assert len(cliente.get("/usuarios/?inicio=1&limite=1").json()) == 1
            assert cliente.get(f"/usuarios/{ids['dono_compartilhada']}").status_code == 200
            assert cliente.get(f"/usuarios/{ids['outro']}").status_code == 403
            assert cliente.get(f"/usuarios/{ids['ex_morador']}").status_code == 403
            assert cliente.patch(f"/usuarios/{ids['outro']}", json={"nome": "X"}).status_code == 403
            assert cliente.delete(f"/usuarios/{ids['outro']}").status_code == 403
    finally:
        app.dependency_overrides.clear()
