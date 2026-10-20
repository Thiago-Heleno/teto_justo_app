import hashlib
import threading
import time
from functools import lru_cache

from fastapi import HTTPException


JANELA_SEGUNDOS = 15 * 60
LIMITE_EMAIL = 5
LIMITE_IP = 20


def _chave(valor: str) -> str:
    return hashlib.sha256(valor.encode()).hexdigest()


class LimitadorLogin:
    """Contadores locais ao processo, com expiração após uma janela fixa."""

    def __init__(self, mensagem: str = "Muitas tentativas de login. Tente novamente mais tarde."):
        self._mensagem = mensagem
        self._contadores: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()
        self._reservas = 0

    def _ler(self, chave: str, agora: float) -> tuple[int, float]:
        contador, expira = self._contadores.get(chave, (0, agora))
        if expira <= agora:
            self._contadores.pop(chave, None)
            return 0, 0
        return contador, expira

    def _estado(
        self, chaves: tuple[str, str], agora: float
    ) -> tuple[int, int, int, int]:
        email, expira_email = self._ler(chaves[0], agora)
        ip, expira_ip = self._ler(chaves[1], agora)
        ttl_email = max(1, int(expira_email - agora)) if email else 0
        ttl_ip = max(1, int(expira_ip - agora)) if ip else 0
        return email, ttl_email, ip, ttl_ip

    @staticmethod
    def _chaves(email: str, ip: str) -> tuple[str, str]:
        email_normalizado = email.strip().casefold()
        return "email:" + _chave(email_normalizado), "ip:" + _chave(ip)

    def _verificar_limite(self, estado: tuple[int, int, int, int]) -> None:
        email, ttl_email, ip, ttl_ip = estado
        esperas = []
        if email >= LIMITE_EMAIL:
            esperas.append(ttl_email)
        if ip >= LIMITE_IP:
            esperas.append(ttl_ip)
        if esperas:
            raise HTTPException(
                status_code=429,
                detail=self._mensagem,
                headers={"Retry-After": str(max(1, max(esperas)))},
            )

    def reservar_tentativa(self, email: str, ip: str) -> None:
        with self._lock:
            agora = time.monotonic()
            self._reservas += 1
            if self._reservas % 256 == 0:
                self._contadores = {
                    chave: estado
                    for chave, estado in self._contadores.items()
                    if estado[1] > agora
                }
            chaves = self._chaves(email, ip)
            estado = self._estado(chaves, agora)
            self._verificar_limite(estado)
            for chave in chaves:
                contador, expira = self._ler(chave, agora)
                if not contador:
                    expira = agora + JANELA_SEGUNDOS
                self._contadores[chave] = (contador + 1, expira)

    def registrar_falha(self, email: str, ip: str) -> None:
        with self._lock:
            agora = time.monotonic()
            chaves = self._chaves(email, ip)
            estado = self._estado(chaves, agora)
            self._verificar_limite(estado)

    def confirmar_sucesso(self, email: str, ip: str) -> None:
        with self._lock:
            agora = time.monotonic()
            chave_email, chave_ip = self._chaves(email, ip)
            self._contadores.pop(chave_email, None)
            contador, expira = self._ler(chave_ip, agora)
            if contador > 1:
                self._contadores[chave_ip] = (contador - 1, expira)
            else:
                self._contadores.pop(chave_ip, None)

    def cancelar_tentativa(self, email: str, ip: str) -> None:
        with self._lock:
            agora = time.monotonic()
            for chave in self._chaves(email, ip):
                contador, expira = self._ler(chave, agora)
                if contador > 1:
                    self._contadores[chave] = (contador - 1, expira)
                else:
                    self._contadores.pop(chave, None)


@lru_cache
def get_limitador_login() -> LimitadorLogin:
    return LimitadorLogin()


@lru_cache
def get_limitador_verificacao() -> LimitadorLogin:
    return LimitadorLogin("Muitas tentativas de verificação. Tente novamente mais tarde.")


@lru_cache
def get_limitador_recuperacao() -> LimitadorLogin:
    return LimitadorLogin("Muitas tentativas de recuperação de senha. Tente novamente mais tarde.")
