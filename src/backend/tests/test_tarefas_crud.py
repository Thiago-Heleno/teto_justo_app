import importlib
import sys
import unittest
from copy import deepcopy
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient


COLUNAS_TAREFA = {
    "nome",
    "descricao",
    "estado_atual",
    "data_fim",
    "fk_casa_id",
    "fk_usuario_id",
}

CAMPOS_ANTIGOS = {
    "title",
    "description",
    "status",
    "due_date",
    "house_id",
    "assigned_to",
    "created_by",
}


class BancoMemoria:
    def __init__(self):
        self.tarefas = {}
        self.atribuicoes = []
        self.payloads_tarefa = []
        self.consultas = 0

    def table(self, nome):
        if nome not in {"tarefa", "atribuida"}:
            raise AssertionError(f"Tabela inesperada: {nome}")
        self.consultas += 1
        return Consulta(self, nome)


class Consulta:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
        self.operacao = "select"
        self.filtros = []
        self.intervalo = None
        self.dados = None
        self.campos = "*"

    def select(self, campos):
        self.operacao = "select"
        self.campos = campos
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
        if self.tabela == "tarefa":
            return self._executar_tarefa()
        return self._executar_atribuida()

    def _corresponde(self, registro):
        return all(
            registro.get(campo) == valor
            for campo, valor in self.filtros
        )

    def _executar_tarefa(self):
        if self.operacao in {"insert", "update"}:
            campos = set(self.dados)
            if not campos <= COLUNAS_TAREFA:
                raise AssertionError(f"Campo inválido para tarefa: {campos}")
            if campos & CAMPOS_ANTIGOS:
                raise AssertionError("O payload ainda contém campos em inglês.")
            if "usuarios_atribuidos" in campos:
                raise AssertionError(
                    "Usuários atribuídos devem ser salvos em atribuida."
                )
            self.banco.payloads_tarefa.append(deepcopy(self.dados))

        if self.operacao == "insert":
            registro = {"id": str(uuid4()), **self.dados}
            self.banco.tarefas[registro["id"]] = registro
            return SimpleNamespace(data=[deepcopy(registro)])

        encontrados = [
            registro
            for registro in self.banco.tarefas.values()
            if self._corresponde(registro)
        ]
        if self.operacao == "select":
            if self.intervalo:
                inicio, fim = self.intervalo
                encontrados = encontrados[inicio: fim + 1]
            return SimpleNamespace(data=deepcopy(encontrados))

        if self.operacao == "update":
            for registro in encontrados:
                registro.update(self.dados)
            return SimpleNamespace(data=deepcopy(encontrados))

        removidos = deepcopy(encontrados)
        for registro in encontrados:
            del self.banco.tarefas[registro["id"]]
        return SimpleNamespace(data=removidos)

    def _executar_atribuida(self):
        if self.operacao == "insert":
            registros = (
                self.dados
                if isinstance(self.dados, list)
                else [self.dados]
            )
            pares = [
                (registro["fk_usuario_id"], registro["fk_tarefa_id"])
                for registro in registros
            ]
            if len(pares) != len(set(pares)):
                raise AssertionError("Atribuição duplicada recebida.")
            self.banco.atribuicoes.extend(deepcopy(registros))
            return SimpleNamespace(data=deepcopy(registros))

        encontrados = [
            registro
            for registro in self.banco.atribuicoes
            if self._corresponde(registro)
        ]
        if self.operacao == "select":
            if self.campos != "*":
                encontrados = [
                    {self.campos: registro[self.campos]}
                    for registro in encontrados
                ]
            return SimpleNamespace(data=deepcopy(encontrados))

        self.banco.atribuicoes = [
            registro
            for registro in self.banco.atribuicoes
            if not self._corresponde(registro)
        ]
        return SimpleNamespace(data=deepcopy(encontrados))


class TarefasCrudTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        modulo_banco = ModuleType("core.database")
        modulo_banco.get_supabase = lambda: None
        with patch.dict(sys.modules, {"core.database": modulo_banco}):
            rotas = importlib.import_module("routers.tarefa")

        cls.dependencia = staticmethod(rotas.get_supabase)
        cls.modulo_servico = importlib.import_module("services.tarefa")
        cls.app = FastAPI()
        cls.app.include_router(rotas.router)

    def setUp(self):
        self.banco = BancoMemoria()
        self.app.dependency_overrides[self.dependencia] = lambda: self.banco
        self.cliente = TestClient(
            self.app,
            raise_server_exceptions=False,
        )
        self.id_casa = str(uuid4())
        self.id_criador = str(uuid4())
        self.id_usuario_1 = str(uuid4())
        self.id_usuario_2 = str(uuid4())

    def tearDown(self):
        self.cliente.close()
        self.app.dependency_overrides.clear()

    def _criar_tarefa(self, usuarios=None):
        payload = {
            "nome": "Limpar cozinha",
            "descricao": "Limpeza semanal",
            "estado_atual": 0,
            "data_fim": "2026-09-20T18:00:00Z",
            "fk_casa_id": self.id_casa,
            "fk_usuario_id": self.id_criador,
        }
        if usuarios is not None:
            payload["usuarios_atribuidos"] = usuarios
        return self.cliente.post("/tarefas/", json=payload)

    def test_criacao_usa_campos_do_banco_e_separa_atribuicoes(self):
        resposta = self._criar_tarefa(
            [self.id_usuario_1, self.id_usuario_1, self.id_usuario_2]
        )

        self.assertEqual(resposta.status_code, 201, resposta.text)
        tarefa = resposta.json()
        self.assertEqual(
            tarefa["usuarios_atribuidos"],
            [self.id_usuario_1, self.id_usuario_2],
        )
        self.assertEqual(set(self.banco.payloads_tarefa[0]), COLUNAS_TAREFA)
        self.assertEqual(len(self.banco.atribuicoes), 2)

    def test_consulta_listagem_e_filtro_por_casa(self):
        criada = self._criar_tarefa([self.id_usuario_1]).json()

        consulta = self.cliente.get(f"/tarefas/{criada['id']}")
        listagem = self.cliente.get("/tarefas/?inicio=0&limite=100")
        por_casa = self.cliente.get(f"/tarefas/casa/{self.id_casa}")

        self.assertEqual(consulta.status_code, 200, consulta.text)
        self.assertEqual(listagem.status_code, 200, listagem.text)
        self.assertEqual(por_casa.status_code, 200, por_casa.text)
        self.assertEqual(len(listagem.json()), 1)
        self.assertEqual(len(por_casa.json()), 1)

    def test_atualizacao_preserva_substitui_e_limpa_atribuicoes(self):
        tarefa = self._criar_tarefa(
            [self.id_usuario_1, self.id_usuario_2]
        ).json()
        caminho = f"/tarefas/{tarefa['id']}"

        resposta = self.cliente.patch(caminho, json={"estado_atual": 1})
        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertEqual(len(resposta.json()["usuarios_atribuidos"]), 2)

        resposta = self.cliente.patch(
            caminho,
            json={"usuarios_atribuidos": [self.id_usuario_2]},
        )
        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertEqual(
            resposta.json()["usuarios_atribuidos"],
            [self.id_usuario_2],
        )

        resposta = self.cliente.patch(
            caminho,
            json={"usuarios_atribuidos": []},
        )
        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertEqual(resposta.json()["usuarios_atribuidos"], [])

    def test_erros_de_validacao_e_registro_inexistente(self):
        consultas_antes = self.banco.consultas
        resposta = self.cliente.get("/tarefas/id-invalido")
        self.assertEqual(resposta.status_code, 422, resposta.text)
        self.assertEqual(self.banco.consultas, consultas_antes)

        id_inexistente = str(uuid4())
        self.assertEqual(
            self.cliente.get(f"/tarefas/{id_inexistente}").status_code,
            404,
        )

        criada = self._criar_tarefa().json()
        resposta = self.cliente.patch(f"/tarefas/{criada['id']}", json={})
        self.assertEqual(resposta.status_code, 400, resposta.text)

    def test_exclusao_remove_tarefa_e_atribuicoes(self):
        tarefa = self._criar_tarefa([self.id_usuario_1]).json()

        resposta = self.cliente.delete(f"/tarefas/{tarefa['id']}")

        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertTrue(resposta.json())
        self.assertNotIn(tarefa["id"], self.banco.tarefas)
        self.assertEqual(self.banco.atribuicoes, [])

    def test_field_map_e_contrato_ingles_foram_removidos(self):
        self.assertFalse(hasattr(self.modulo_servico, "FIELD_MAP"))
        resposta = self.cliente.post(
            "/tarefas/",
            json={
                "title": "Contrato antigo",
                "status": 0,
                "due_date": "2026-09-20T18:00:00Z",
                "house_id": self.id_casa,
                "created_by": self.id_criador,
            },
        )
        self.assertEqual(resposta.status_code, 422, resposta.text)

        especificacao = self.app.openapi()
        self.assertNotIn("/tasks/", especificacao["paths"])
        for nome_schema in (
            "TarefaCriar",
            "TarefaAtualizar",
            "TarefaResposta",
        ):
            propriedades = set(
                especificacao["components"]["schemas"][nome_schema][
                    "properties"
                ]
            )
            self.assertFalse(propriedades & CAMPOS_ANTIGOS)


if __name__ == "__main__":
    unittest.main()
