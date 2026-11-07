from base64 import b64decode
from binascii import Error

from fastapi import HTTPException


def foto_para_banco(foto: str) -> str:
    try:
        conteudo = b64decode(foto, validate=True)
    except (Error, ValueError) as erro:
        raise HTTPException(status_code=400, detail="A foto deve estar em Base64 válido.") from erro

    return "\\x" + conteudo.hex()
