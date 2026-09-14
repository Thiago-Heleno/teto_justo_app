import importlib
import sys
import unittest
from copy import deepcopy
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient


# Banco falso em memória usado como substituto do Supabase real: injetado via
# dependency_overrides do FastAPI para os testes de integração das rotas de
# usuário rodarem sem depender de um banco externo.
class BancoMemoria:
    def __init__(self):
        self.usuarios = {}

    def table(self, nome):
        if nome != "usuario":
            raise AssertionError(f"Tabela inesperada: {nome}")
        return Consulta(self)


# Reproduz a interface fluente do client do Supabase (table().select().eq()...
# .execute()), guardando operação/filtros/dados até execute() aplicar tudo
# sobre o dicionário do BancoMemoria.
class Consulta:
    def __init__(self, banco):
        self.banco = banco
        self.operacao = "select"
        self.filtros = []
        self.dados = None

    def select(self, _campos):
        self.operacao = "select"
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor))
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

    # Executa a operação guardada (insert/select/update/delete) sobre o banco
    # em memória e devolve um objeto com `.data`, no mesmo formato do retorno
    # real do Supabase, para as rotas funcionarem sem precisar de alterações.
    def execute(self):
        encontrados = [
            usuario
            for usuario in self.banco.usuarios.values()
            if all(usuario.get(campo) == valor for campo, valor in self.filtros)
        ]
        if self.operacao == "insert":
            registro = {"id": str(uuid4()), **self.dados}
            self.banco.usuarios[registro["id"]] = registro
            return SimpleNamespace(data=[deepcopy(registro)])
        if self.operacao == "select":
            return SimpleNamespace(data=deepcopy(encontrados))
        if self.operacao == "update":
            for usuario in encontrados:
                usuario.update(self.dados)
            return SimpleNamespace(data=deepcopy(encontrados))
        for usuario in encontrados:
            del self.banco.usuarios[usuario["id"]]
        return SimpleNamespace(data=deepcopy(encontrados))


# Testes de integração das rotas de usuário: sobem uma FastAPI real com o
# router de usuário e um TestClient, trocando apenas a dependência do Supabase
# pelo BancoMemoria, para validar o fluxo completo de CRUD via HTTP.
class UsuariosCrudTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Importa o módulo de rotas com "core.database" mockado, evitando que
        # a importação tente criar uma conexão real com o Supabase.
        modulo_banco = ModuleType("core.database")
        modulo_banco.get_supabase = lambda: None
        with patch.dict(sys.modules, {"core.database": modulo_banco}):
            rotas = importlib.import_module("routers.usuario")

        cls.dependencia = staticmethod(rotas.get_supabase)
        cls.app = FastAPI()
        cls.app.include_router(rotas.router)

    def setUp(self):
        # Cria um banco em memória novo e isolado para cada teste, sobrescrevendo
        # a dependência get_supabase para usá-lo no lugar do banco real.
        self.banco = BancoMemoria()
        self.app.dependency_overrides[self.dependencia] = lambda: self.banco
        self.cliente = TestClient(self.app, raise_server_exceptions=False)

    def tearDown(self):
        self.cliente.close()
        self.app.dependency_overrides.clear()

    # Helper que monta e envia um payload válido de criação de usuário,
    # permitindo sobrescrever campos específicos em cada teste.
    def _criar_usuario(self, **sobrescritas):
        payload = {
            "nome": "Ana Silva",
            "email": "ana@example.com",
            "telefone": None,
            "senha": "Teste-123!",
            "foto": None,
            "usuario_tipo": 0,
        }
        payload.update(sobrescritas)
        return self.cliente.post("/usuarios/", json=payload)

    # Percorre o ciclo completo de CRUD: cria, busca, atualiza parcialmente,
    # deleta e confirma que o usuário deixa de existir depois de deletado.
    def test_crud_completo(self):
        criado = self._criar_usuario()
        self.assertEqual(criado.status_code, 201, criado.text)
        usuario = criado.json()
        self.assertEqual(usuario["email"], "ana@example.com")
        self.assertNotIn("senha", usuario)
        self.assertNotIn("senha_hash", usuario)

        busca = self.cliente.get(f"/usuarios/{usuario['id']}")
        self.assertEqual(busca.status_code, 200, busca.text)
        self.assertEqual(busca.json()["nome"], "Ana Silva")

        atualizado = self.cliente.patch(
            f"/usuarios/{usuario['id']}",
            json={"nome": "Ana Paula Silva"},
        )
        self.assertEqual(atualizado.status_code, 200, atualizado.text)
        self.assertEqual(atualizado.json()["nome"], "Ana Paula Silva")

        excluido = self.cliente.delete(f"/usuarios/{usuario['id']}")
        self.assertEqual(excluido.status_code, 204, excluido.text)
        self.assertEqual(excluido.content, b"")

        self.assertEqual(
            self.cliente.get(f"/usuarios/{usuario['id']}").status_code,
            404,
        )

    # Garante que a API rejeita a criação de um segundo usuário com o mesmo
    # e-mail de um já cadastrado.
    def test_email_duplicado_retorna_400(self):
        primeiro = self._criar_usuario()
        self.assertEqual(primeiro.status_code, 201, primeiro.text)

        segundo = self._criar_usuario(nome="Outra Ana")
        self.assertEqual(segundo.status_code, 400, segundo.text)

    # Cobre casos de erro das rotas: payload inválido (422), id malformado
    # (422) e operações (GET/PATCH/DELETE) sobre ids inexistentes (404/400).
    def test_validacoes_e_erros(self):
        self.assertEqual(
            self._criar_usuario(email="email-invalido").status_code,
            422,
        )
        self.assertEqual(
            self.cliente.post("/usuarios/", json={"nome": "Ana"}).status_code,
            422,
        )
        self.assertEqual(
            self.cliente.get("/usuarios/id-invalido").status_code,
            422,
        )
        self.assertEqual(
            self.cliente.get(f"/usuarios/{uuid4()}").status_code,
            404,
        )
        self.assertEqual(
            self.cliente.patch(f"/usuarios/{uuid4()}", json={}).status_code,
            400,
        )
        self.assertEqual(
            self.cliente.patch(
                f"/usuarios/{uuid4()}",
                json={"nome": "Alguém"},
            ).status_code,
            404,
        )
        self.assertEqual(
            self.cliente.delete(f"/usuarios/{uuid4()}").status_code,
            404,
        )


if __name__ == "__main__":
    unittest.main()
