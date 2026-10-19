import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException


_DURACAO_CODIGO = timedelta(minutes=10)
_ROTULO_CHAVE = b"verificacao-email"
_ERRO_CODIGO = "Código inválido ou expirado."

# Cores e fontes do DESIGN.md (Caldera), com fallbacks seguros para clientes de e-mail.
_TEXTO = "font-family:'DM Sans',Arial,Helvetica,sans-serif;font-weight:500;color:#070607;"
_TITULO = "font-family:Impact,'Arial Narrow',sans-serif;font-weight:400;color:#070607;"


def _chave() -> bytes:
    # Subchave da mesma chave dos convites: não exige nova variável de ambiente.
    segredo = os.getenv("CASA_CONVITE_SECRET", "").encode("utf-8")
    if len(segredo) < 32:
        raise HTTPException(status_code=503, detail="Serviço de verificação indisponível.")
    return hmac.new(segredo, _ROTULO_CHAVE, hashlib.sha256).digest()


def _assinar(email: str, exp: int, codigo: str) -> str:
    conteudo = f"{email.strip().casefold()}|{exp}|{codigo}".encode("utf-8")
    return hmac.new(_chave(), conteudo, hashlib.sha256).hexdigest()


class ServicoVerificacaoEmail:
    """Código de 5 dígitos sem estado: o token só prova que o código foi emitido para o e-mail."""

    def emitir(self, email: str) -> dict:
        codigo = str(secrets.randbelow(90000) + 10000)
        exp = int((datetime.now(timezone.utc) + _DURACAO_CODIGO).timestamp())
        return {
            "codigo": codigo,
            "token_verificacao": f"{exp}.{_assinar(email, exp, codigo)}",
            "expira_em": datetime.fromtimestamp(exp, timezone.utc),
        }

    def verificar(self, email: str, codigo: str, token: str) -> None:
        try:
            parte_exp, assinatura = token.split(".")
            exp = int(parte_exp)
        except (AttributeError, ValueError) as erro:
            raise HTTPException(status_code=400, detail=_ERRO_CODIGO) from erro
        esperada = _assinar(email, exp, codigo)
        if exp <= datetime.now(timezone.utc).timestamp() or not hmac.compare_digest(
            assinatura.encode("utf-8"), esperada.encode("utf-8")
        ):
            raise HTTPException(status_code=400, detail=_ERRO_CODIGO)

    @staticmethod
    def montar_html(codigo: str) -> str:
        faixa = "background:#e2e2df;padding:32px 16px;"
        cartao = "max-width:480px;background:#f7f6f2;border-radius:40px;"
        marca = "margin:0 0 24px;font-size:14px;font-weight:800;letter-spacing:2px;color:#fc5000;"
        titulo = "margin:0 0 16px;font-size:32px;line-height:1;letter-spacing:0.64px;"
        bloco = "margin:0 0 24px;padding:16px;background:#f5f28e;border-radius:20px;"
        bloco += "text-align:center;font-size:48px;line-height:1;letter-spacing:12px;"
        tabela = 'role="presentation" width="100%" cellpadding="0" cellspacing="0"'
        return (
            f'<table {tabela} style="{faixa}"><tr><td align="center">'
            f'<table {tabela} style="{cartao}"><tr>'
            f'<td style="padding:40px;{_TEXTO}">'
            f'<p style="{marca}">TETO JUSTO</p>'
            f'<h1 style="{titulo}{_TITULO}">Confirme seu e-mail</h1>'
            '<p style="margin:0 0 24px;font-size:16px;line-height:1.55;">'
            "Use o código abaixo para concluir seu cadastro.</p>"
            f'<p style="{bloco}{_TITULO}">{codigo}</p>'
            '<p style="margin:0 0 8px;font-size:14px;line-height:1.55;">'
            "O código vale por 10 minutos.</p>"
            '<p style="margin:0;font-family:Arial,Helvetica,sans-serif;font-size:12px;'
            'line-height:1.2;">Se você não pediu este código, ignore este e-mail.</p>'
            "</td></tr></table></td></tr></table>"
        )
