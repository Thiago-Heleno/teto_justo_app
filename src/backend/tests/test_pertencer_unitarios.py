"""Testes unitários do serviço de pertencer."""

import unittest
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from postgrest.exceptions import APIError

from schemas.pertencer import PertencerCriar
from services.pertencer import ServicoPertencer


# Banco falso em memória, usado no lugar do Supabase real para os testes
# unitários do ServicoPertencer não dependerem de rede/infra externa.
class BancoMemoria:
    def __init__(self):
        self.vinculos = {}  # dict: (fk_usuario_id, fk_casa_id) -> dict com os campos do vínculo
        self.resultados_vazios = set()
        self.eventos = []
        self.proprietario = None

    def table(self, nome):
        if nome not in {"pertencer", "casa", "score_event"}:
            raise AssertionError(f"Tabela inesperada: {nome}")
        return Consulta(self, nome)

    def rpc(self, nome, parametros):
        assert nome == "excluir_vinculo_sem_credito"
        return ChamadaRpc(self, parametros)


class ChamadaRpc:
    def __init__(self, banco, parametros):
        self.banco = banco
        self.parametros = parametros

    def execute(self):
        usuario_id = self.parametros["p_id_usuario"]
        casa_id = self.parametros["p_id_casa"]
        chave = (usuario_id, casa_id)
        if chave not in self.banco.vinculos:
            return SimpleNamespace(data=False)
        if any(
            evento["fk_usuario_id"] == usuario_id
            and evento["fk_casa_id"] == casa_id
            for evento in self.banco.eventos
        ):
            raise APIError({"code": "PT409", "message": "Vínculo com histórico."})
        del self.banco.vinculos[chave]
        return SimpleNamespace(data=True)


# Imita a interface fluente do client do Supabase (table().select().eq().execute()),
# armazenando a operação e os filtros pedidos até o execute() ser chamado.
class Consulta:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
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
        self.dados = dict(dados)
        return self

    # Devolve a mesma estrutura básica de resposta das consultas ao Supabase.
    def execute(self):
        if self.tabela == "casa":
            return SimpleNamespace(data=(
                [{"fk_usuario_id": self.banco.proprietario}]
                if self.banco.proprietario else []
            ))
        if self.tabela == "score_event":
            return SimpleNamespace(data=[
                evento for evento in self.banco.eventos
                if all(evento.get(c) == valor for c, valor in self.filtros)
            ])
        if self.operacao in self.banco.resultados_vazios:
            self.banco.resultados_vazios.remove(self.operacao)
            return SimpleNamespace(data=[])

        encontrados = [
            v for v in self.banco.vinculos.values()
            if all(v.get(c) == valor for c, valor in self.filtros)
        ]

        if self.operacao == "insert":
            chave = (self.dados["fk_usuario_id"], self.dados["fk_casa_id"])
            registro = dict(self.dados)
            self.banco.vinculos[chave] = registro
            return SimpleNamespace(data=[dict(registro)])

        if self.operacao == "select":
            if self.intervalo:
                inicio, fim = self.intervalo
                encontrados = encontrados[inicio: fim + 1]
            return SimpleNamespace(data=[dict(v) for v in encontrados])

class TesteServicoPertencer(unittest.TestCase):
    # Monta um ServicoPertencer com o banco em memória e dois UUIDs fixos
    # (usuário e casa) reaproveitados pela maioria dos testes desta classe.
    def setUp(self):
        self.banco = BancoMemoria()
        self.servico = ServicoPertencer(self.banco)
        self.fk_usuario_id = uuid4()
        self.fk_casa_id = uuid4()

    # Atalho para criar o vínculo padrão (usuário/casa fixos do setUp).
    def _criar_vinculo(self):
        dados = PertencerCriar(
            fk_usuario_id=self.fk_usuario_id,
            fk_casa_id=self.fk_casa_id,
        )
        return self.servico.criar_pertencer(dados)

    # O vínculo inicia com saldo zero e IDs serializados.
    def test_criar_pertencer_com_sucesso(self):
        resultado = self._criar_vinculo()

        self.assertEqual(resultado["fk_usuario_id"], str(self.fk_usuario_id))
        self.assertEqual(resultado["fk_casa_id"], str(self.fk_casa_id))
        self.assertEqual(resultado["score"], 0)

    def test_criar_pertencer_rejeita_score_arbitrario(self):
        with self.assertRaises(ValidationError):
            PertencerCriar(
                fk_usuario_id=self.fk_usuario_id,
                fk_casa_id=self.fk_casa_id,
                score=10,
            )

    # Tentar criar o mesmo par usuário/casa duas vezes deve ser rejeitado.
    def test_criar_pertencer_duplicado_gera_400(self):
        self._criar_vinculo()

        with self.assertRaises(HTTPException) as contexto:
            self._criar_vinculo()

        self.assertEqual(contexto.exception.status_code, 400)

    # Se o insert não devolver dado nenhum (falha do banco), a criação deve
    # virar um erro 500 em vez de repassar uma resposta vazia.
    def test_criar_pertencer_sem_retorno_do_banco_gera_500(self):
        self.banco.resultados_vazios.add("insert")

        with self.assertRaises(HTTPException) as contexto:
            self._criar_vinculo()

        self.assertEqual(contexto.exception.status_code, 500)

    # Busca por um vínculo que existe deve devolver os dados persistidos.
    def test_buscar_pertencer_existente(self):
        self._criar_vinculo()

        resultado = self.servico.buscar_pertencer(self.fk_usuario_id, self.fk_casa_id)

        self.assertEqual(resultado["score"], 0)

    # Busca por uma chave (usuário, casa) que não tem vínculo deve dar 404.
    def test_buscar_pertencer_inexistente_gera_404(self):
        with self.assertRaises(HTTPException) as contexto:
            self.servico.buscar_pertencer(uuid4(), uuid4())

        self.assertEqual(contexto.exception.status_code, 404)

    # Com 3 vínculos cadastrados, pedir inicio=1/limite=1 deve devolver
    # exatamente um registro (a fatia do meio).
    def test_listar_pertencer_respeita_paginacao(self):
        self._criar_vinculo()
        for _ in range(2):
            self.servico.criar_pertencer(
                PertencerCriar(fk_usuario_id=uuid4(), fk_casa_id=uuid4(), score=0)
            )

        resultado = self.servico.listar_pertencer(inicio=1, limite=1)

        self.assertEqual(len(resultado), 1)

    # Excluir um vínculo existente deve remover a entrada do banco e
    # devolver True, confirmando a exclusão.
    def test_deletar_pertencer_com_sucesso(self):
        self._criar_vinculo()

        resultado = self.servico.deletar_pertencer(self.fk_usuario_id, self.fk_casa_id)

        self.assertTrue(resultado)
        self.assertNotIn(
            (str(self.fk_usuario_id), str(self.fk_casa_id)), self.banco.vinculos
        )

    # Excluir um vínculo que já não existe (ou nunca existiu) deve dar 404.
    def test_deletar_pertencer_inexistente_gera_404(self):
        with self.assertRaises(HTTPException) as contexto:
            self.servico.deletar_pertencer(uuid4(), uuid4())

        self.assertEqual(contexto.exception.status_code, 404)

    def test_deletar_pertencer_com_evento_gera_409(self):
        self._criar_vinculo()
        self.banco.eventos.append({
            "id": str(uuid4()),
            "fk_usuario_id": str(self.fk_usuario_id),
            "fk_casa_id": str(self.fk_casa_id),
        })

        with self.assertRaises(HTTPException) as contexto:
            self.servico.deletar_pertencer(self.fk_usuario_id, self.fk_casa_id)

        self.assertEqual(contexto.exception.status_code, 409)

    def test_deletar_proprietario_gera_409(self):
        self._criar_vinculo()
        self.banco.proprietario = str(self.fk_usuario_id)

        with self.assertRaises(HTTPException) as contexto:
            self.servico.deletar_pertencer(self.fk_usuario_id, self.fk_casa_id)

        self.assertEqual(contexto.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
