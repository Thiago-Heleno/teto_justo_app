import unittest

import bcrypt
from fastapi import HTTPException

from test_usuarios_uuid import BancoMemoria
from schemas.usuario import UsuarioCriar
from services.usuario import ServicoUsuario


class TesteHash(unittest.TestCase):
    def test_hash_e_diferente_da_senha_original(self):
        senha = "123"

        hash_gerado = bcrypt.hashpw(
            senha.encode("utf-8"), bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

        self.assertNotEqual(senha, hash_gerado)


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


if __name__ == "__main__":
    unittest.main()
