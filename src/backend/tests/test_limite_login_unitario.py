import pytest
from fastapi import HTTPException

from services.limite_login import LimitadorLogin


@pytest.fixture
def relogio(monkeypatch):
    agora = [0.0]
    monkeypatch.setattr("services.limite_login.time.monotonic", lambda: agora[0])
    return agora


def test_bloqueio_por_email_expira_e_sucesso_limpa_falhas(relogio):
    limitador = LimitadorLogin()
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

    relogio[0] = 900
    limitador.reservar_tentativa("morador@example.com", "10.0.0.2")
    limitador.registrar_falha("morador@example.com", "10.0.0.2")
    limitador.confirmar_sucesso("morador@example.com", "10.0.0.2")
    limitador.reservar_tentativa("morador@example.com", "10.0.0.2")


def test_bloqueio_por_ip_agrega_emails_diferentes(relogio):
    limitador = LimitadorLogin()
    for numero in range(19):
        email = f"morador{numero}@example.com"
        limitador.reservar_tentativa(email, "10.0.0.1")
        limitador.registrar_falha(email, "10.0.0.1")
    limitador.reservar_tentativa("novo@example.com", "10.0.0.1")
    with pytest.raises(HTTPException) as erro:
        limitador.registrar_falha("novo@example.com", "10.0.0.1")
    assert erro.value.status_code == 429
    assert erro.value.headers["Retry-After"] == "900"
    with pytest.raises(HTTPException):
        limitador.reservar_tentativa("outro@example.com", "10.0.0.1")
    limitador.reservar_tentativa("outro@example.com", "10.0.0.2")


def test_chaves_nao_expoem_email_ou_ip(relogio):
    limitador = LimitadorLogin()
    limitador.reservar_tentativa("morador@example.com", "10.0.0.1")
    assert len(limitador._contadores) == 2
    assert all(
        "morador" not in chave and "10.0.0.1" not in chave
        for chave in limitador._contadores
    )


def test_reservas_concorrentes_nao_ultrapassam_limite(relogio):
    limitador = LimitadorLogin()
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
    app.dependency_overrides[get_supabase] = object
    app.dependency_overrides[get_limitador_login] = LimitadorLogin
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
