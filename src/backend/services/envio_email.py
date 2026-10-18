import os

import httpx
from fastapi import HTTPException


_URL_RESEND = "https://api.resend.com/emails"
_REMETENTE_PADRAO = "onboarding@resend.dev"
_TIMEOUT_SEGUNDOS = 10


class ServicoEmail:
    def enviar(self, para: str | list[str], assunto: str, html: str) -> None:
        chave = os.getenv("RESEND_API")
        if not chave:
            raise HTTPException(status_code=503, detail="Serviço de email indisponível.")
        remetente = os.getenv("RESEND_FROM") or _REMETENTE_PADRAO
        try:
            resposta = httpx.post(
                _URL_RESEND,
                headers={"Authorization": f"Bearer {chave}"},
                json={"from": remetente, "to": para, "subject": assunto, "html": html},
                timeout=_TIMEOUT_SEGUNDOS,
            )
            resposta.raise_for_status()
        except httpx.HTTPError as erro:
            # Mensagem genérica: o erro original pode conter a chave ou o destinatário.
            raise HTTPException(
                status_code=503, detail="Não foi possível enviar o email."
            ) from erro
