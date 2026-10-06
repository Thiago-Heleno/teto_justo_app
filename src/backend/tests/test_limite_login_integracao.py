"""Exercita os scripts de contagem no Redis isolado de teste."""

import os
import time
from uuid import uuid4

import pytest
from fastapi import HTTPException
from redis import Redis

from services.limite_login import LimitadorLogin


def test_limite_compartilhado_e_expiracao_no_redis():
    url = os.environ["REDIS_URL"]
    redis = Redis.from_url(url, decode_responses=True)
    limitador_a = LimitadorLogin(redis)
    limitador_b = LimitadorLogin(Redis.from_url(url, decode_responses=True))
    email = f"limite-{uuid4().hex}@example.com"
    ip = f"teste-{uuid4().hex}"
    chave_email, chave_ip = limitador_a._chaves(email, ip)
    try:
        for _ in range(4):
            limitador_a.reservar_tentativa(email, ip)
            limitador_a.registrar_falha(email, ip)
        limitador_b.reservar_tentativa(email, ip)
        with pytest.raises(HTTPException) as erro:
            limitador_b.registrar_falha(email, ip)
        assert erro.value.status_code == 429
        assert 1 <= int(erro.value.headers["Retry-After"]) <= 900

        redis.expire(chave_email, 1)
        time.sleep(1.2)
        limitador_a.reservar_tentativa(email, ip)
    finally:
        redis.delete(chave_email, chave_ip)
