import importlib
import sys
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient


class BancoMemoria:
    def __init__(self):
        self.sessoes = {}

    def table(self, nome):
        if nome != "sessao":
            raise AssertionError(f"Tabela inesperada: {nome}")
        return Consulta(self)


class Consulta:
    def __init__(self, banco):
        self.banco = banco
        self.operacao = "select"
        self.filtros = []
        self.intervalo = None
        self.dados = None

    def select(self, _campos):
        self.operacao = "select"
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor))
        return self

    def range(self, inicio, fim):
        self.intervalo = (inicio, fim)
        return self

    def insert(self, dados):
        self.operacao = "insert"
        self.dados = deepcopy(dados)
        return self

    def update(self, dados):
        self.operacao = "update"
        self.dados = deepcopy(dados)
        return self

    def delete(self):
        self.operacao = "delete"
        return self

    def execute(self):
        encontrados = [
            sessao
            for sessao in self.banco.sessoes.values()
            if all(sessao.get(campo) == valor for campo, valor in self.filtros)
        ]
        if self.operacao == "insert":
            registro = {
                "id": str(uuid4()),
                "criado_em": datetime.now(timezone.utc).isoformat(),
                **self.dados,
            }
            self.banco.sessoes[registro["id"]] = registro
            return SimpleNamespace(data=[deepcopy(registro)])
        if self.operacao == "select":
            if self.intervalo:
                inicio, fim = self.intervalo
                encontrados = encontrados[inicio : fim + 1]
            return SimpleNamespace(data=deepcopy(encontrados))
        if self.operacao == "update":
            for sessao in encontrados:
                sessao.update(self.dados)
            return SimpleNamespace(data=deepcopy(encontrados))
        for sessao in encontrados:
            del self.banco.sessoes[sessao["id"]]
        return SimpleNamespace(data=deepcopy(encontrados))


class SessoesCrudTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        modulo_banco = ModuleType("core.database")
        modulo_banco.get_supabase = lambda: None
        with patch.dict(sys.modules, {"core.database": modulo_banco}):
            rotas = importlib.import_module("routers.sessao")

        cls.dependencia = staticmethod(rotas.get_supabase)
        cls.app = FastAPI()
        cls.app.include_router(rotas.router)

    def setUp(self):
        self.banco = BancoMemoria()
        self.app.dependency_overrides[self.dependencia] = lambda: self.banco
        self.cliente = TestClient(self.app, raise_server_exceptions=False)
        self.id_usuario = str(uuid4())

    def tearDown(self):
        self.cliente.close()
        self.app.dependency_overrides.clear()

    def _criar_sessao(self):
        return self.cliente.post(
            "/sessoes/",
            json={
                "token": "token-de-login-seguro",  # nosec B105 - dado fake de teste, nao e credencial real
                "expira_em": "2026-10-01T12:00:00Z",
                "fk_usuario_id": self.id_usuario,
            },
        )

    def test_crud_completo(self):
        criada = self._criar_sessao()
        self.assertEqual(criada.status_code, 201, criada.text)
        sessao = criada.json()
        self.assertEqual(sessao["fk_usuario_id"], self.id_usuario)
        self.assertIn("criado_em", sessao)

        self.assertEqual(
            self.cliente.get(f"/sessoes/{sessao['id']}").status_code,
            200,
        )
        self.assertEqual(len(self.cliente.get("/sessoes/").json()), 1)

        atualizada = self.cliente.patch(
            f"/sessoes/{sessao['id']}",
            json={"expira_em": "2026-11-01T12:00:00Z"},
        )
        self.assertEqual(atualizada.status_code, 200, atualizada.text)
        self.assertEqual(atualizada.json()["expira_em"], "2026-11-01T12:00:00Z")

        excluida = self.cliente.delete(f"/sessoes/{sessao['id']}")
        self.assertEqual(excluida.status_code, 200, excluida.text)
        self.assertTrue(excluida.json())
        self.assertEqual(
            self.cliente.get(f"/sessoes/{sessao['id']}").status_code,
            404,
        )

    def test_validacoes_e_erros(self):
        self.assertEqual(
            self.cliente.post("/sessoes/", json={}).status_code,
            422,
        )
        self.assertEqual(
            self.cliente.get("/sessoes/id-invalido").status_code,
            422,
        )
        self.assertEqual(
            self.cliente.patch(f"/sessoes/{uuid4()}", json={}).status_code,
            400,
        )
        self.assertEqual(
            self.cliente.delete(f"/sessoes/{uuid4()}").status_code,
            404,
        )


if __name__ == "__main__":
    unittest.main()
