import base64
import importlib
import sys
import unittest
from copy import deepcopy
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient


COLUNAS_CASA = {"nome", "endereco", "foto", "fk_usuario_id"}
COLUNAS_ATUALIZAVEIS = {"nome", "endereco", "foto"}

FOTO_BYTES = b"fachada da casa"
FOTO_BASE64 = base64.b64encode(FOTO_BYTES).decode("ascii")
FOTO_BANCO = "\\x" + FOTO_BYTES.hex()


class BancoMemoria:
    def __init__(self):
        self.casas = {}
        self.payloads = []
        self.intervalos = []
        self.consultas = 0
        self.resultados_vazios = set()

    def table(self, nome):
        if nome != "casa":
            raise AssertionError(f"Tabela inesperada: {nome}")
        self.consultas += 1
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
        self.banco.intervalos.append(self.intervalo)
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
        if self.operacao in self.banco.resultados_vazios:
            self.banco.resultados_vazios.remove(self.operacao)
            return SimpleNamespace(data=[])

        if self.operacao in {"insert", "update"}:
            campos_permitidos = (
                COLUNAS_CASA
                if self.operacao == "insert"
                else COLUNAS_ATUALIZAVEIS
            )
            if not set(self.dados) <= campos_permitidos:
                raise AssertionError(f"Payload inválido: {self.dados}")
            foto = self.dados.get("foto")
            if foto is not None and not foto.startswith("\\x"):
                raise AssertionError("Foto não convertida para BYTEA hexadecimal.")
            self.banco.payloads.append(
                (self.operacao, deepcopy(self.dados))
            )

        if self.operacao == "insert":
            registro = {"id": str(uuid4()), **self.dados}
            self.banco.casas[registro["id"]] = registro
            return SimpleNamespace(data=[deepcopy(registro)])

        encontrados = [
            registro
            for registro in self.banco.casas.values()
            if all(
                registro.get(campo) == valor
                for campo, valor in self.filtros
            )
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
            del self.banco.casas[registro["id"]]
        return SimpleNamespace(data=removidos)


class CasasCrudTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        modulo_banco = ModuleType("core.database")
        modulo_banco.get_supabase = lambda: None
        with patch.dict(sys.modules, {"core.database": modulo_banco}):
            rotas = importlib.import_module("routers.casa")

        cls.dependencia = staticmethod(rotas.get_supabase)
        cls.modulo_servico = importlib.import_module("services.casa")
        cls.app = FastAPI()
        cls.app.include_router(rotas.router)

    def setUp(self):
        self.banco = BancoMemoria()
        self.app.dependency_overrides[self.dependencia] = lambda: self.banco
        self.cliente = TestClient(
            self.app,
            raise_server_exceptions=False,
        )
        self.id_dono = str(uuid4())

    def tearDown(self):
        self.cliente.close()
        self.app.dependency_overrides.clear()

    def _criar_casa(self, nome="Casa Azul", foto=FOTO_BASE64):
        return self.cliente.post(
            "/casas/",
            json={
                "nome": nome,
                "endereco": "Rua das Flores, 10",
                "foto": foto,
                "fk_usuario_id": self.id_dono,
            },
        )

    def test_criacao_converte_foto_e_usa_campos_do_banco(self):
        resposta = self._criar_casa()

        self.assertEqual(resposta.status_code, 201, resposta.text)
        self.assertEqual(resposta.json()["foto"], FOTO_BASE64)
        operacao, payload = self.banco.payloads[0]
        self.assertEqual(operacao, "insert")
        self.assertEqual(set(payload), COLUNAS_CASA)
        self.assertEqual(payload["foto"], FOTO_BANCO)
        self.assertEqual(payload["fk_usuario_id"], self.id_dono)
        self.assertFalse(hasattr(self.modulo_servico, "FIELD_MAP"))

    def test_criacao_sem_foto_e_base64_invalido(self):
        resposta = self._criar_casa(foto=None)
        self.assertEqual(resposta.status_code, 201, resposta.text)
        self.assertIsNone(resposta.json()["foto"])

        consultas_antes = self.banco.consultas
        resposta = self._criar_casa(foto="%%%")
        self.assertEqual(resposta.status_code, 400, resposta.text)
        self.assertEqual(
            resposta.json()["detail"],
            "A foto deve estar em Base64 válido.",
        )
        self.assertEqual(self.banco.consultas, consultas_antes)

    def test_busca_listagem_e_paginacao(self):
        primeira = self._criar_casa(nome="Casa 1").json()
        segunda = self._criar_casa(nome="Casa 2").json()

        resposta = self.cliente.get(f"/casas/{primeira['id']}")
        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertEqual(resposta.json()["foto"], FOTO_BASE64)

        resposta = self.cliente.get("/casas/?inicio=1&limite=1")
        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertEqual([casa["id"] for casa in resposta.json()], [segunda["id"]])
        self.assertEqual(self.banco.intervalos[-1], (1, 1))

    def test_atualizacao_parcial_preserva_dono_e_converte_foto(self):
        casa = self._criar_casa().json()
        outro_dono = str(uuid4())
        nova_foto_bytes = b"nova fachada"
        nova_foto = base64.b64encode(nova_foto_bytes).decode("ascii")

        resposta = self.cliente.patch(
            f"/casas/{casa['id']}",
            json={
                "nome": "Casa Verde",
                "foto": nova_foto,
                "fk_usuario_id": outro_dono,
            },
        )

        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertEqual(resposta.json()["nome"], "Casa Verde")
        self.assertEqual(resposta.json()["foto"], nova_foto)
        self.assertEqual(resposta.json()["fk_usuario_id"], self.id_dono)
        operacao, payload = self.banco.payloads[-1]
        self.assertEqual(operacao, "update")
        self.assertEqual(set(payload), {"nome", "foto"})
        self.assertEqual(payload["foto"], "\\x" + nova_foto_bytes.hex())

    def test_erros_de_atualizacao_busca_e_exclusao(self):
        resposta = self.cliente.patch(f"/casas/{uuid4()}", json={})
        self.assertEqual(resposta.status_code, 400, resposta.text)

        consultas_antes = self.banco.consultas
        resposta = self.cliente.get("/casas/id-invalido")
        self.assertEqual(resposta.status_code, 422, resposta.text)
        self.assertEqual(self.banco.consultas, consultas_antes)

        id_inexistente = str(uuid4())
        self.assertEqual(
            self.cliente.get(f"/casas/{id_inexistente}").status_code,
            404,
        )
        self.assertEqual(
            self.cliente.delete(f"/casas/{id_inexistente}").status_code,
            404,
        )

    def test_exclusao_e_erros_de_persistencia(self):
        casa = self._criar_casa().json()
        resposta = self.cliente.delete(f"/casas/{casa['id']}")
        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertTrue(resposta.json())
        self.assertNotIn(casa["id"], self.banco.casas)

        self.banco.resultados_vazios.add("insert")
        resposta = self._criar_casa()
        self.assertEqual(resposta.status_code, 500, resposta.text)

    def test_formato_invalido_no_banco_e_contrato_openapi(self):
        id_casa = str(uuid4())
        self.banco.casas[id_casa] = {
            "id": id_casa,
            "nome": "Casa com foto inválida",
            "endereco": "Rua A",
            "foto": "\\xzz",
            "fk_usuario_id": self.id_dono,
        }

        resposta = self.cliente.get(f"/casas/{id_casa}")
        self.assertEqual(resposta.status_code, 500, resposta.text)
        self.assertEqual(
            resposta.json()["detail"],
            "Formato de foto inválido no banco.",
        )

        especificacao = self.app.openapi()
        self.assertIn("/casas/", especificacao["paths"])
        self.assertIn("/casas/{id_casa}", especificacao["paths"])
        for nome_schema in (
            "CasaCriar",
            "CasaAtualizar",
            "CasaResposta",
        ):
            propriedades = set(
                especificacao["components"]["schemas"][nome_schema][
                    "properties"
                ]
            )
            self.assertTrue(
                propriedades <= {
                    "id",
                    "nome",
                    "endereco",
                    "foto",
                    "fk_usuario_id",
                }
            )


if __name__ == "__main__":
    unittest.main()
