import unittest
from uuid import uuid4

import bcrypt
from fastapi import HTTPException
from postgrest.exceptions import APIError

from types import SimpleNamespace
from unittest.mock import MagicMock

from schemas.usuario import UsuarioAtualizar, UsuarioCriar
from services.usuario import ServicoUsuario


# Banco falso em memória, usado no lugar do Supabase real para os testes
# unitários do ServicoUsuario não dependerem de rede/infra externa.
class BancoMemoria:
    def __init__(self):
        self.usuarios = {}  # dict: id -> dict com os campos do usuário
        self.casas = {}  # dict: id -> dict com os campos da casa
        self.outras = {}  # tabela -> {id: registro} (pertencer, tarefa, ...)
        self.com_historico = False  # simula as FKs RESTRICT ao apagar usuário

    def table(self, nome):
        if nome == "usuario":
            return Consulta(self, self.usuarios, bloqueia_delete=self.com_historico)
        if nome == "casa":
            return Consulta(self, self.casas)
        return Consulta(self, self.outras.setdefault(nome, {}))


# Imita a interface fluente do client do Supabase (table().select().eq().execute()),
# armazenando a operação e os filtros pedidos até o execute() ser chamado.
class Consulta:
    def __init__(self, banco, registros, bloqueia_delete=False):
        self.banco = banco
        self.registros = registros
        self.bloqueia_delete = bloqueia_delete
        self.operacao = "select"
        self.filtros = []
        self.dados = None

    def select(self, _campos):
        self.operacao = "select"
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor, True))
        return self

    def neq(self, campo, valor):
        self.filtros.append((campo, valor, False))
        return self

    def in_(self, campo, valores):
        self.filtros.append((campo, valores, "in"))
        return self

    def limit(self, _quantidade):
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
    # retorno da lib do Supabase, para o ServicoUsuario funcionar sem alterações.
    def execute(self):
        from types import SimpleNamespace
        from uuid import uuid4

        encontrados = [
            u for u in self.registros.values()
            if all(
                (u.get(c) in v) if igual == "in" else (u.get(c) == v) == igual
                for c, v, igual in self.filtros
            )
        ]
        if self.operacao == "insert":
            registro = {"id": str(uuid4()), **self.dados}
            self.registros[registro["id"]] = registro
            return SimpleNamespace(data=[dict(registro)])
        if self.operacao == "select":
            return SimpleNamespace(data=[dict(u) for u in encontrados])
        if self.operacao == "update":
            for u in encontrados:
                u.update(self.dados)
            return SimpleNamespace(data=[dict(u) for u in encontrados])
        # delete
        if self.bloqueia_delete:
            raise APIError({"code": "23503", "message": "foreign key violation"})
        for u in encontrados:
            del self.registros[u["id"]]
        return SimpleNamespace(data=[dict(u) for u in encontrados])


# Testa a geração de hash de senha com bcrypt.
class TesteHash(unittest.TestCase):
    def test_hash_e_diferente_da_senha_original(self):
        senha = "123"

        hash_gerado = bcrypt.hashpw(
            senha.encode("utf-8"), bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

        self.assertNotEqual(senha, hash_gerado)


# Testes do método criar_usuario: garante que a criação falha com 400 quando
# já existe um usuário cadastrado com o mesmo e-mail.
class TesteCriarUsuarioUnitario(unittest.TestCase):
    def test_email_duplicado_gera_erro_400(self):
        banco = MagicMock()
        consulta = banco.table.return_value

        consulta.select.return_value = consulta
        consulta.eq.return_value = consulta
        consulta.execute.return_value = SimpleNamespace(
            data=[
                {
                    "id": "id-qualquer",
                    "email": "ana@example.com",
                }
            ]
        )

        servico = ServicoUsuario(banco)
        dados = UsuarioCriar(
            nome="Outra Ana",
            email="ana@example.com",
            telefone=None,
            senha="Teste-123!",
        )

        with self.assertRaises(HTTPException) as erro:
            servico.criar_usuario(dados)

        self.assertEqual(erro.exception.status_code, 400)
        self.assertEqual(
            erro.exception.detail,
            "E-mail já cadastrado.",
        )


# Testes do método buscar_usuario: deve retornar o usuário quando ele existe
# no banco e levantar 404 quando o id não é encontrado.
class TesteBuscarUsuarioUnitario(unittest.TestCase):
    # Usuário presente no banco: buscar_usuario deve retornar os dados dele.
    def test_busca_usuario_existente_retorna_dados(self):
        banco = BancoMemoria()
        id_usuario = str(uuid4())
        banco.usuarios[id_usuario] = {"id": id_usuario, "nome": "Ana", "email": "ana@example.com"}
        servico = ServicoUsuario(banco)

        encontrado = servico.buscar_usuario(id_usuario)

        self.assertEqual(encontrado["id"], id_usuario)
        self.assertEqual(encontrado["nome"], "Ana")

    # Banco vazio: buscar por um id que não existe deve levantar HTTPException 404.
    def test_busca_usuario_inexistente_gera_erro_404(self):
        banco = BancoMemoria()
        servico = ServicoUsuario(banco)

        with self.assertRaises(HTTPException) as contexto:
            servico.buscar_usuario(uuid4())

        self.assertEqual(contexto.exception.status_code, 404)


# Testes do método atualizar_usuario: cobre atualização parcial (só os campos
# informados mudam), erro 400 quando nenhum dado é enviado e erro 404 quando
# o usuário não existe.
class TesteAtualizarUsuarioUnitario(unittest.TestCase):
    # Envia apenas o campo "nome" e confirma que ele muda, mas os demais
    # campos (ex.: email) permanecem intactos.
    def test_atualizacao_parcial_altera_apenas_campos_informados(self):
        banco = BancoMemoria()
        id_usuario = str(uuid4())
        banco.usuarios[id_usuario] = {
            "id": id_usuario,
            "nome": "Ana",
            "email": "ana@example.com",
            "telefone": None,
        }
        servico = ServicoUsuario(banco)
        dados = UsuarioAtualizar(nome="Ana Paula")

        atualizado = servico.atualizar_usuario(id_usuario, dados)

        self.assertEqual(atualizado["nome"], "Ana Paula")
        self.assertEqual(atualizado["email"], "ana@example.com")

    # UsuarioAtualizar() sem nenhum campo preenchido deve ser rejeitado com 400,
    # já que não há nada para atualizar.
    def test_atualizacao_sem_dados_gera_erro_400(self):
        banco = BancoMemoria()
        id_usuario = str(uuid4())
        banco.usuarios[id_usuario] = {"id": id_usuario, "nome": "Ana"}
        servico = ServicoUsuario(banco)
        dados = UsuarioAtualizar()

        with self.assertRaises(HTTPException) as contexto:
            servico.atualizar_usuario(id_usuario, dados)

        self.assertEqual(contexto.exception.status_code, 400)

    # Trocar para o e-mail de outra conta é recusado; manter o próprio e-mail é aceito.
    def test_atualizacao_rejeita_email_de_outra_conta(self):
        banco = BancoMemoria()
        id_usuario, id_outro = str(uuid4()), str(uuid4())
        banco.usuarios[id_usuario] = {"id": id_usuario, "email": "ana@example.com"}
        banco.usuarios[id_outro] = {"id": id_outro, "email": "bia@example.com"}
        servico = ServicoUsuario(banco)

        with self.assertRaises(HTTPException) as contexto:
            servico.atualizar_usuario(id_usuario, UsuarioAtualizar(email="bia@example.com"))

        self.assertEqual(contexto.exception.status_code, 400)
        self.assertEqual(banco.usuarios[id_usuario]["email"], "ana@example.com")
        atualizado = servico.atualizar_usuario(
            id_usuario, UsuarioAtualizar(email="ana@example.com")
        )
        self.assertEqual(atualizado["email"], "ana@example.com")

    # Tenta atualizar um id que não está no banco: deve levantar 404.
    def test_atualizacao_usuario_inexistente_gera_erro_404(self):
        banco = BancoMemoria()
        servico = ServicoUsuario(banco)
        dados = UsuarioAtualizar(nome="Ana Paula")

        with self.assertRaises(HTTPException) as contexto:
            servico.atualizar_usuario(uuid4(), dados)

        self.assertEqual(contexto.exception.status_code, 404)


# Testes do método deletar_usuario: remove o usuário existente do banco em
# memória e levanta 404 ao tentar deletar um id que não existe.
class TesteDeletarUsuarioUnitario(unittest.TestCase):
    # Usuário existente é removido do banco em memória após deletar_usuario.
    def test_delecao_remove_usuario_do_banco(self):
        banco = BancoMemoria()
        id_usuario = str(uuid4())
        banco.usuarios[id_usuario] = {"id": id_usuario, "nome": "Ana"}
        servico = ServicoUsuario(banco)

        resultado = servico.deletar_usuario(id_usuario)

        self.assertTrue(resultado)
        self.assertNotIn(id_usuario, banco.usuarios)

    # Tenta deletar um id que não existe no banco: deve levantar 404.
    def test_delecao_usuario_inexistente_gera_erro_404(self):
        banco = BancoMemoria()
        servico = ServicoUsuario(banco)

        with self.assertRaises(HTTPException) as contexto:
            servico.deletar_usuario(uuid4())

        self.assertEqual(contexto.exception.status_code, 404)

    # Proprietário de casa recebe 409 com mensagem clara e a conta é preservada.
    def test_delecao_de_proprietario_gera_erro_409(self):
        banco = BancoMemoria()
        id_usuario, id_casa = str(uuid4()), str(uuid4())
        banco.usuarios[id_usuario] = {"id": id_usuario, "nome": "Ana"}
        banco.casas[id_casa] = {"id": id_casa, "fk_usuario_id": id_usuario}
        servico = ServicoUsuario(banco)

        with self.assertRaises(HTTPException) as contexto:
            servico.deletar_usuario(id_usuario)

        self.assertEqual(contexto.exception.status_code, 409)
        self.assertIn("proprietário de uma casa", contexto.exception.detail)
        self.assertIn(id_usuario, banco.usuarios)

    def _banco_com_historico(self):
        banco = BancoMemoria()
        banco.com_historico = True
        self.id_usuario, self.id_casa = str(uuid4()), str(uuid4())
        banco.usuarios[self.id_usuario] = {
            "id": self.id_usuario, "nome": "Ana", "email": "ana@example.com",
            "telefone": 1199, "foto": "abc", "senha_hash": "hash",
        }
        banco.casas[self.id_casa] = {
            "id": self.id_casa, "fk_usuario_id": str(uuid4()), "rotacao_versao": 0,
        }
        banco.outras["pertencer"] = {"v": {
            "id": "v", "fk_usuario_id": self.id_usuario,
            "fk_casa_id": self.id_casa, "ativo": True,
        }}
        banco.outras["sessao"] = {"s": {"id": "s", "fk_usuario_id": self.id_usuario}}
        return banco

    # Conta com histórico (FK RESTRICT) é anonimizada: sai da casa, perde as
    # sessões e as credenciais, e o registro continua para preservar o histórico.
    def test_delecao_com_historico_anonimiza_a_conta(self):
        banco = self._banco_com_historico()

        self.assertTrue(ServicoUsuario(banco).deletar_usuario(self.id_usuario))

        usuario = banco.usuarios[self.id_usuario]
        self.assertEqual(usuario["nome"], "Usuário removido")
        self.assertNotEqual(usuario["email"], "ana@example.com")
        self.assertIsNone(usuario["senha_hash"])
        self.assertIsNone(usuario["telefone"])
        self.assertIsNone(usuario["foto"])
        self.assertFalse(banco.outras["pertencer"]["v"]["ativo"])
        self.assertEqual(banco.outras["sessao"], {})

    # Tarefa aberta impede a exclusão e nada é alterado.
    def test_delecao_com_tarefa_aberta_gera_erro_409(self):
        banco = self._banco_com_historico()
        banco.outras["atribuida"] = {"a": {
            "id": "a", "fk_usuario_id": self.id_usuario, "fk_tarefa_id": "t1",
        }}
        banco.outras["tarefa"] = {"t1": {"id": "t1", "estado_atual": "pendente"}}

        with self.assertRaises(HTTPException) as contexto:
            ServicoUsuario(banco).deletar_usuario(self.id_usuario)

        self.assertEqual(contexto.exception.status_code, 409)
        self.assertEqual(banco.usuarios[self.id_usuario]["nome"], "Ana")
        self.assertTrue(banco.outras["pertencer"]["v"]["ativo"])
        self.assertIn("s", banco.outras["sessao"])


if __name__ == "__main__":
    unittest.main()
