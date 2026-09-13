"""Verifica o contrato HTTP real sem credenciais ou conexao com o Supabase.

Executar na pasta src/backend: python -m unittest discover -s tests -v
Requer as dependencias de requirements.txt e httpx.
"""

import importlib
import sys
import unittest
from copy import deepcopy
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient


class BancoMemoria:
    def __init__(self):
        self.usuarios = {}
        self.consultas = 0

    def table(self, nome):
        if nome != "usuario":
            raise AssertionError(f"Tabela inesperada: {nome}")
        self.consultas += 1
        return Consulta(self)


class Consulta:
    def __init__(self, banco):
        self.banco = banco
        self.filtros = []
        self.operacao = "select"
        self.dados = {}

    def select(self, campos):
        return self

    def eq(self, campo, valor):
        # O contrato do adaptador exige IDs serializados como texto.
        if campo == "id" and not isinstance(valor, str):
            raise AssertionError("UUID deve ser convertido para texto no filtro")
        self.filtros.append((campo, valor))
        return self

    def insert(self, dados):
        self.operacao, self.dados = "insert", deepcopy(dados)
        return self

    def update(self, dados):
        self.operacao, self.dados = "update", deepcopy(dados)
        return self

    def execute(self):
        if self.operacao == "insert":
            registro = {"id": str(uuid4()), **self.dados}
            self.banco.usuarios[registro["id"]] = registro
            return SimpleNamespace(data=[deepcopy(registro)])
        registros = [
            registro for registro in self.banco.usuarios.values()
            if all(registro.get(campo) == valor for campo, valor in self.filtros)
        ]
        if self.operacao == "update":
            for registro in registros:
                registro.update(self.dados)
        return SimpleNamespace(data=deepcopy(registros))


class UsuariosUUIDTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Evita executar core.database, que cria o cliente ao ser importado.
        # As rotas, schemas, servico e hash de senha continuam sendo reais.
        modulo = ModuleType("core.database")
        modulo.get_supabase = lambda: None
        with patch.dict(sys.modules, {"core.database": modulo}):
            rotas = importlib.import_module("routers.usuario")
        cls.dependencia = staticmethod(rotas.get_supabase)
        cls.app = FastAPI()
        cls.app.include_router(rotas.router)

    def setUp(self):
        self.banco = BancoMemoria()
        self.app.dependency_overrides[self.dependencia] = lambda: self.banco
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.id = str(uuid4())
        self.outro_id = str(uuid4())
        self.banco.usuarios = {
            self.id: {"id": self.id, "nome": "Ana", "email": "ana@example.com",
                      "telefone": "11999990000", "senha_hash": "hash-de-fixture"},
            self.outro_id: {"id": self.outro_id, "nome": "Bia", "email": "bia@example.com"},
        }

    def tearDown(self):
        self.client.close()
        self.app.dependency_overrides.clear()

    def test_cadastro_retorna_uuid_e_permite_consulta(self):
        resposta = self.client.post("/usuarios/", json={
            "nome": "Carlos", "email": "carlos@example.com",
            "telefone": "11999991111", "senha": "Teste-local-123!",
        })
        self.assertEqual(resposta.status_code, 201, resposta.text)
        usuario = resposta.json()
        UUID(usuario["id"])
        self.assertNotIn("senha", usuario)
        self.assertNotIn("senha_hash", usuario)
        self.assertEqual(self.client.get(f"/usuarios/{usuario['id']}").json(), usuario)

    def test_consulta_uuid_existente(self):
        resposta = self.client.get(f"/usuarios/{self.id}")
        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertEqual(resposta.json(), {
            "id": self.id, "nome": "Ana", "email": "ana@example.com",
        })

    def test_atualizacao_persiste_e_nao_altera_outro_usuario(self):
        outro_antes = deepcopy(self.banco.usuarios[self.outro_id])
        resposta = self.client.patch(f"/usuarios/{self.id}", json={"nome": "Ana Silva"})
        self.assertEqual(resposta.status_code, 200, resposta.text)
        consulta = self.client.get(f"/usuarios/{self.id}")
        self.assertEqual(consulta.status_code, 200)
        self.assertEqual(consulta.json()["nome"], "Ana Silva")
        self.assertEqual(self.banco.usuarios[self.id]["telefone"], "11999990000")
        self.assertEqual(self.banco.usuarios[self.outro_id], outro_antes)

    def test_id_invalido_retorna_422_sem_consultar_banco(self):
        for identificador in ("abc", "123"):
            for metodo in ("GET", "PATCH"):
                with self.subTest(id=identificador, metodo=metodo):
                    kwargs = {"json": {"nome": "Teste"}} if metodo == "PATCH" else {}
                    resposta = self.client.request(metodo, f"/usuarios/{identificador}", **kwargs)
                    self.assertEqual(resposta.status_code, 422, resposta.text)
        self.assertEqual(self.banco.consultas, 0)

    def test_uuid_inexistente_retorna_404(self):
        inexistente = str(uuid4())
        for metodo in ("GET", "PATCH"):
            with self.subTest(metodo=metodo):
                kwargs = {"json": {"nome": "Teste"}} if metodo == "PATCH" else {}
                resposta = self.client.request(metodo, f"/usuarios/{inexistente}", **kwargs)
                self.assertEqual(resposta.status_code, 404, resposta.text)


if __name__ == "__main__":
    unittest.main()
