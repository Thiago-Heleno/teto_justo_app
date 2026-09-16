"""Testes unitários do serviço de pertencer."""

import unittest
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException

from schemas.pertencer import PertencerAtualizar, PertencerCriar
from services.pertencer import ServicoPertencer


# Banco falso em memória, usado no lugar do Supabase real para os testes
# unitários do ServicoPertencer não dependerem de rede/infra externa.
class BancoMemoria:
    def __init__(self):
        self.vinculos = {}  # dict: (fk_usuario_id, fk_casa_id) -> dict com os campos do vínculo
        self.resultados_vazios = set()

    def table(self, nome):
        if nome != "pertencer":
            raise AssertionError(f"Tabela inesperada: {nome}")
        return Consulta(self)


# Imita a interface fluente do client do Supabase (table().select().eq().execute()),
# armazenando a operação e os filtros pedidos até o execute() ser chamado.
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
        self.dados = dict(dados)
        return self

    def update(self, dados):
        self.operacao = "update"
        self.dados = dict(dados)
        return self

    def delete(self):
        self.operacao = "delete"
        return self

    # Executa de fato a operação guardada (insert/select/update/delete) sobre o
    # dicionário em memória e devolve um objeto com atributo `.data`, igual ao
    # retorno da lib do Supabase, para o ServicoPertencer funcionar sem alterações.
    def execute(self):
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

        if self.operacao == "update":
            for v in encontrados:
                v.update(self.dados)
            return SimpleNamespace(data=[dict(v) for v in encontrados])

        # delete
        for v in encontrados:
            del self.banco.vinculos[(v["fk_usuario_id"], v["fk_casa_id"])]
        return SimpleNamespace(data=[dict(v) for v in encontrados])


class TesteServicoPertencer(unittest.TestCase):
    # Monta um ServicoPertencer com o banco em memória e dois UUIDs fixos
    # (usuário e casa) reaproveitados pela maioria dos testes desta classe.
    def setUp(self):
        self.banco = BancoMemoria()
        self.servico = ServicoPertencer(self.banco)
        self.fk_usuario_id = uuid4()
        self.fk_casa_id = uuid4()

    # Atalho para criar o vínculo padrão (usuário/casa fixos do setUp) com um
    # score à escolha, evitando repetir o PertencerCriar em cada teste.
    def _criar_vinculo(self, score=0):
        dados = PertencerCriar(
            fk_usuario_id=self.fk_usuario_id,
            fk_casa_id=self.fk_casa_id,
            score=score,
        )
        return self.servico.criar_pertencer(dados)

    # Cria um vínculo novo e confere que a resposta traz os ids como string
    # (mode="json") e o score informado.
    def test_criar_pertencer_com_sucesso(self):
        resultado = self._criar_vinculo(score=10)

        self.assertEqual(resultado["fk_usuario_id"], str(self.fk_usuario_id))
        self.assertEqual(resultado["fk_casa_id"], str(self.fk_casa_id))
        self.assertEqual(resultado["score"], 10)

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
        self._criar_vinculo(score=5)

        resultado = self.servico.buscar_pertencer(self.fk_usuario_id, self.fk_casa_id)

        self.assertEqual(resultado["score"], 5)

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

    # Atualizar o score de um vínculo existente deve refletir o novo valor.
    def test_atualizar_pertencer_com_sucesso(self):
        self._criar_vinculo(score=0)

        resultado = self.servico.atualizar_pertencer(
            self.fk_usuario_id,
            self.fk_casa_id,
            PertencerAtualizar(score=20),
        )

        self.assertEqual(resultado["score"], 20)

    # Atualizar um vínculo que não existe deve dar 404, sem criar nada.
    def test_atualizar_pertencer_inexistente_gera_404(self):
        with self.assertRaises(HTTPException) as contexto:
            self.servico.atualizar_pertencer(
                uuid4(), uuid4(), PertencerAtualizar(score=20)
            )

        self.assertEqual(contexto.exception.status_code, 404)

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


if __name__ == "__main__":
    unittest.main()
