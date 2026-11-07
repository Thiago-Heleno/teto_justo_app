from base64 import b64encode
from uuid import uuid4

import pytest

from schemas.casa import MoradorResposta
from schemas.usuario import UsuarioResposta


@pytest.mark.parametrize("modelo", [UsuarioResposta, MoradorResposta])
@pytest.mark.parametrize("como_texto", [False, True], ids=["binario", "base64-legado"])
def test_foto_salva_e_exibida_em_base64(modelo, como_texto):
    imagem = b"\x89PNG\r\n\x1a\n"
    esperado = b64encode(imagem)
    salvo = esperado if como_texto else imagem
    resposta = modelo(
        id=uuid4(), nome="Ana", email="ana@example.com", score=0, foto="\\x" + salvo.hex()
    )

    assert resposta.model_dump(mode="json")["foto"] == esperado.decode("ascii")
