import unittest
from uuid import uuid4

import bcrypt
from fastapi import HTTPException

from schemas.usuario import UsuarioAtualizar, UsuarioCriar
from services.usuario import ServicoUsuario


# Banco falso em memória, usado no lugar do Supabase real para os testes
# unitários do ServicoUsuario não dependerem de rede/infra externa.
class BancoMemoria:
    def __init__(self):
        self.usuarios = {}  # dict: id -> dict com os campos do usuário

    def table(self, nome):
        if nome != "usuario":
            raise AssertionError(f"Tabela inesperada: {nome}")
        return Consulta(self)


# Imita a interface fluente do client do Supabase (table().select().eq().execute()),
# armazenando a operação e os filtros pedidos até o execute() ser chamado.
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
            u for u in self.banco.usuarios.values()
            if all(u.get(c) == v for c, v in self.filtros)
        ]
        if self.operacao == "insert":
            registro = {"id": str(uuid4()), **self.dados}
            self.banco.usuarios[registro["id"]] = registro
            return SimpleNamespace(data=[dict(registro)])
        if self.operacao == "select":
            return SimpleNamespace(data=[dict(u) for u in encontrados])
        if self.operacao == "update":
            for u in encontrados:
                u.update(self.dados)
            return SimpleNamespace(data=[dict(u) for u in encontrados])
        # delete
        for u in encontrados:
            del self.banco.usuarios[u["id"]]
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
        # Arrange: banco fake ja com um usuario cadastrado com esse email
        banco = BancoMemoria()
        banco.usuarios["id-qualquer"] = {"id": "id-qualquer", "email": "ana@example.com"}
        # inseriu um teste fake no banco
        servico = ServicoUsuario(banco)
        dados = UsuarioCriar(
            nome="Outra Ana", email="ana@example.com", telefone=None, senha="Teste-123!"
        )

        # Act + Assert
        with self.assertRaises(HTTPException):
            servico.criar_usuario(dados)


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


if __name__ == "__main__":
    unittest.main()
