import hashlib
import os
from functools import lru_cache

from fastapi import HTTPException
from redis import Redis, RedisError


JANELA_SEGUNDOS = 15 * 60
LIMITE_EMAIL = 5
LIMITE_IP = 20

_ESTADO = """
return {tonumber(redis.call('GET', KEYS[1]) or '0'), redis.call('TTL', KEYS[1]),
        tonumber(redis.call('GET', KEYS[2]) or '0'), redis.call('TTL', KEYS[2])}
"""
_RESERVAR = """
local email_atual = tonumber(redis.call('GET', KEYS[1]) or '0')
local ip_atual = tonumber(redis.call('GET', KEYS[2]) or '0')
if email_atual >= tonumber(ARGV[2]) or ip_atual >= tonumber(ARGV[3]) then
  return {email_atual, redis.call('TTL', KEYS[1]),
          ip_atual, redis.call('TTL', KEYS[2]), 0}
end
local email = redis.call('INCR', KEYS[1])
if email == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
local ip = redis.call('INCR', KEYS[2])
if ip == 1 then redis.call('EXPIRE', KEYS[2], ARGV[1]) end
return {email, redis.call('TTL', KEYS[1]), ip, redis.call('TTL', KEYS[2]), 1}
"""
_SUCESSO = """
redis.call('DEL', KEYS[1])
local ip = tonumber(redis.call('GET', KEYS[2]) or '0')
if ip > 1 then redis.call('DECR', KEYS[2]) else redis.call('DEL', KEYS[2]) end
return 1
"""
_CANCELAR = """
for i = 1, 2 do
  local atual = tonumber(redis.call('GET', KEYS[i]) or '0')
  if atual > 1 then redis.call('DECR', KEYS[i])
  elseif atual == 1 then redis.call('DEL', KEYS[i]) end
end
return 1
"""


def _indisponivel() -> HTTPException:
    return HTTPException(status_code=503, detail="Login temporariamente indisponível.")


class LimitadorLogin:
    def __init__(self, redis: Redis):
        self.redis = redis

    @staticmethod
    def _chaves(email: str, ip: str) -> tuple[str, str]:
        email_normalizado = email.strip().casefold()
        return (
            "login:email:" + hashlib.sha256(email_normalizado.encode()).hexdigest(),
            "login:ip:" + hashlib.sha256(ip.encode()).hexdigest(),
        )

    @staticmethod
    def _conferir_limite(estado: list[int]) -> None:
        email, ttl_email, ip, ttl_ip = (int(valor) for valor in estado)
        esperas = []
        if email >= LIMITE_EMAIL:
            esperas.append(ttl_email)
        if ip >= LIMITE_IP:
            esperas.append(ttl_ip)
        if esperas:
            espera = max(1, max(esperas))
            raise HTTPException(
                status_code=429,
                detail="Muitas tentativas de login. Tente novamente mais tarde.",
                headers={"Retry-After": str(espera)},
            )

    def reservar_tentativa(self, email: str, ip: str) -> None:
        try:
            estado = self.redis.eval(
                _RESERVAR, 2, *self._chaves(email, ip),
                JANELA_SEGUNDOS, LIMITE_EMAIL, LIMITE_IP,
            )
        except (RedisError, OSError) as erro:
            raise _indisponivel() from erro
        if int(estado[4]) == 0:
            self._conferir_limite(estado[:4])

    def registrar_falha(self, email: str, ip: str) -> None:
        try:
            estado = self.redis.eval(_ESTADO, 2, *self._chaves(email, ip))
        except (RedisError, OSError) as erro:
            raise _indisponivel() from erro
        self._conferir_limite(estado)

    def confirmar_sucesso(self, email: str, ip: str) -> None:
        try:
            self.redis.eval(_SUCESSO, 2, *self._chaves(email, ip))
        except (RedisError, OSError) as erro:
            raise _indisponivel() from erro

    def cancelar_tentativa(self, email: str, ip: str) -> None:
        try:
            self.redis.eval(_CANCELAR, 2, *self._chaves(email, ip))
        except (RedisError, OSError) as erro:
            raise _indisponivel() from erro


@lru_cache
def get_limitador_login() -> LimitadorLogin:
    url = os.getenv("REDIS_URL")
    if not url:
        raise _indisponivel()
    try:
        cliente = Redis.from_url(
            url, socket_connect_timeout=1, socket_timeout=1, decode_responses=True
        )
    except (ValueError, RedisError) as erro:
        raise _indisponivel() from erro
    return LimitadorLogin(cliente)
