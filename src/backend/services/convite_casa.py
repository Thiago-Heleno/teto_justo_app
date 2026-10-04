import base64
import binascii
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException


_DURACAO_CONVITE = timedelta(hours=24)
_CAMPOS_CONVITE = {"v", "casa_id", "emissor_id", "exp"}


def _chave_convite() -> bytes:
    segredo = os.getenv("CASA_CONVITE_SECRET", "").encode("utf-8")
    if len(segredo) < 32:
        raise HTTPException(status_code=503, detail="Serviço de convites indisponível.")
    return segredo


def _base64url(conteudo: bytes) -> str:
    return base64.urlsafe_b64encode(conteudo).rstrip(b"=").decode("ascii")


def _decodificar_base64url(valor: str) -> bytes:
    conteudo = base64.b64decode(valor + "=" * (-len(valor) % 4), altchars=b"-_", validate=True)
    if _base64url(conteudo) != valor:
        raise ValueError("Base64 não canônico")
    return conteudo


class ServicoConviteCasa:
    def emitir(self, id_casa: UUID, id_proprietario: UUID) -> dict:
        chave = _chave_convite()
        exp = int((datetime.now(timezone.utc) + _DURACAO_CONVITE).timestamp())
        dados = {
            "v": 1,
            "casa_id": str(id_casa),
            "emissor_id": str(id_proprietario),
            "exp": exp,
        }
        conteudo = json.dumps(dados, sort_keys=True, separators=(",", ":")).encode("utf-8")
        assinatura = hmac.new(chave, conteudo, hashlib.sha256).digest()
        return {
            "convite": f"{_base64url(conteudo)}.{_base64url(assinatura)}",
            "expira_em": datetime.fromtimestamp(exp, timezone.utc),
        }

    def verificar(self, convite: str) -> tuple[UUID, UUID]:
        chave = _chave_convite()
        try:
            if not isinstance(convite, str):
                raise ValueError("Convite não é texto")
            parte_dados, parte_assinatura = convite.split(".")
            conteudo = _decodificar_base64url(parte_dados)
            assinatura = _decodificar_base64url(parte_assinatura)
            assinatura_esperada = hmac.new(chave, conteudo, hashlib.sha256).digest()
            if not hmac.compare_digest(assinatura, assinatura_esperada):
                raise ValueError("Assinatura inválida")

            dados = json.loads(conteudo)
            if (
                not isinstance(dados, dict)
                or set(dados) != _CAMPOS_CONVITE
                or type(dados["v"]) is not int
                or dados["v"] != 1
                or type(dados["exp"]) is not int
                or type(dados["casa_id"]) is not str
                or type(dados["emissor_id"]) is not str
                or dados["exp"] <= datetime.now(timezone.utc).timestamp()
            ):
                raise ValueError("Convite expirado ou malformado")
            id_casa = UUID(dados["casa_id"])
            id_emissor = UUID(dados["emissor_id"])
        except (
            binascii.Error,
            ValueError,
            TypeError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as erro:
            raise HTTPException(status_code=400, detail="Convite inválido ou expirado.") from erro
        return id_casa, id_emissor
