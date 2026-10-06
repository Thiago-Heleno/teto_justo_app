import pytest
from fastapi import HTTPException
from redis import RedisError

from services.limite_login import (
    LimitadorLogin, _CANCELAR, _ESTADO, _RESERVAR, _SUCESSO,
)


class RedisEmMemoria:
    def __init__(self):
        self.agora = 0
        self.contadores = {}
        self.falhar = False

    def _ler(self, chave):
        contador, expira = self.contadores.get(chave, (0, 0))
        if expira <= self.agora:
            self.contadores.pop(chave, None)
            return 0, -2
        return contador, expira - self.agora

    def eval(self, script, _quantidade, *argumentos):
        if self.falhar:
            raise RedisError("indisponível")
        chaves = argumentos[:2]
        if script == _RESERVAR:
            estado = [valor for chave in chaves for valor in self._ler(chave)]
            if estado[0] >= int(argumentos[3]) or estado[2] >= int(argumentos[4]):
                return estado + [0]
            janela = int(argumentos[2])
            for chave in chaves:
                contador, ttl = self._ler(chave)
                self.contadores[chave] = (
                    contador + 1,
                    self.agora + (ttl if ttl > 0 else janela),
                )
        elif script == _SUCESSO:
            self.contadores.pop(chaves[0], None)
            contador, ttl = self._ler(chaves[1])
            if contador > 1:
                self.contadores[chaves[1]] = (contador - 1, self.agora + ttl)
            else:
                self.contadores.pop(chaves[1], None)
            return 1
        elif script == _CANCELAR:
            for chave in chaves:
                contador, ttl = self._ler(chave)
                if contador > 1:
                    self.contadores[chave] = (contador - 1, self.agora + ttl)
                else:
                    self.contadores.pop(chave, None)
            return 1
        else:
            assert script == _ESTADO
        email, ttl_email = self._ler(chaves[0])
        ip, ttl_ip = self._ler(chaves[1])
        estado = [email, ttl_email, ip, ttl_ip]
        return estado + [1] if script == _RESERVAR else estado

    def delete(self, chave):
        if self.falhar:
            raise RedisError("indisponível")
        self.contadores.pop(chave, None)


def test_bloqueio_por_email_expira_e_sucesso_limpa_falhas():
    redis = RedisEmMemoria()
    limitador = LimitadorLogin(redis)
    for _ in range(4):
        limitador.reservar_tentativa("Morador@Example.com", "10.0.0.1")
        limitador.registrar_falha("morador@example.com", "10.0.0.1")
    limitador.reservar_tentativa("morador@example.com", "10.0.0.1")
    with pytest.raises(HTTPException) as erro:
        limitador.registrar_falha("morador@example.com", "10.0.0.1")
    assert erro.value.status_code == 429
    assert erro.value.headers == {"Retry-After": "900"}
    with pytest.raises(HTTPException, match="Muitas tentativas"):
        limitador.reservar_tentativa("MORADOR@example.com", "10.0.0.2")

    redis.agora = 900
    limitador.reservar_tentativa("morador@example.com", "10.0.0.2")
    limitador.registrar_falha("morador@example.com", "10.0.0.2")
    limitador.confirmar_sucesso("morador@example.com", "10.0.0.2")
    limitador.reservar_tentativa("morador@example.com", "10.0.0.2")


def test_bloqueio_por_ip_agrega_emails_diferentes():
    redis = RedisEmMemoria()
    limitador = LimitadorLogin(redis)
    for numero in range(19):
        limitador.reservar_tentativa(f"morador{numero}@example.com", "10.0.0.1")
        limitador.registrar_falha(f"morador{numero}@example.com", "10.0.0.1")
    limitador.reservar_tentativa("novo@example.com", "10.0.0.1")
    with pytest.raises(HTTPException) as erro:
        limitador.registrar_falha("novo@example.com", "10.0.0.1")
    assert erro.value.status_code == 429
    assert erro.value.headers["Retry-After"] == "900"
    with pytest.raises(HTTPException):
        limitador.reservar_tentativa("outro@example.com", "10.0.0.1")
    limitador.reservar_tentativa("outro@example.com", "10.0.0.2")


def test_redis_indisponivel_impede_login():
    redis = RedisEmMemoria()
    redis.falhar = True
    limitador = LimitadorLogin(redis)
    for operacao in (
        limitador.reservar_tentativa,
        limitador.registrar_falha,
        limitador.confirmar_sucesso,
        limitador.cancelar_tentativa,
    ):
        with pytest.raises(HTTPException) as erro:
            operacao("morador@example.com", "10.0.0.1")
        assert erro.value.status_code == 503


def test_chaves_nao_expoem_email_ou_ip():
    redis = RedisEmMemoria()
    LimitadorLogin(redis).reservar_tentativa("morador@example.com", "10.0.0.1")
    assert len(redis.contadores) == 2
    assert all("morador" not in chave and "10.0.0.1" not in chave for chave in redis.contadores)


def test_reservas_concorrentes_nao_ultrapassam_limite():
    redis = RedisEmMemoria()
    limitador = LimitadorLogin(redis)
    for _ in range(5):
        limitador.reservar_tentativa("morador@example.com", "10.0.0.1")
    with pytest.raises(HTTPException) as erro:
        limitador.reservar_tentativa("morador@example.com", "10.0.0.2")
    assert erro.value.status_code == 429
    limitador.cancelar_tentativa("morador@example.com", "10.0.0.1")
    limitador.reservar_tentativa("morador@example.com", "10.0.0.2")


def test_rota_bloqueia_antes_da_sexta_verificacao_de_senha(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
    monkeypatch.setenv("SUPABASE_KEY", "unit-test-placeholder")
    from fastapi.testclient import TestClient

    from core.database import get_supabase
    from main import app
    from services.limite_login import get_limitador_login
    from services.sessao import ServicoSessao

    chamadas = []

    def senha_incorreta(_self, _dados, antes_de_emitir_token=None):
        chamadas.append(1)
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")

    monkeypatch.setattr(ServicoSessao, "login", senha_incorreta)
    redis = RedisEmMemoria()
    app.dependency_overrides[get_supabase] = object
    app.dependency_overrides[get_limitador_login] = lambda: LimitadorLogin(redis)
    try:
        with TestClient(app) as cliente:
            codigos = [
                cliente.post(
                    "/sessoes/login", json={"email": "morador@example.com", "senha": "x"}
                ).status_code
                for _ in range(6)
            ]
        assert codigos == [401, 401, 401, 401, 429, 429]
        assert len(chamadas) == 5
    finally:
        app.dependency_overrides.clear()
