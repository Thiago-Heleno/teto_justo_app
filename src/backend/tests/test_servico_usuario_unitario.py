import unittest

import bcrypt
from fastapi import HTTPException

from types import SimpleNamespace

from unittest.mock import MagicMock
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


if __name__ == "__main__":
    unittest.main()
