import os


def origens_frontend() -> list[str]:
    valor = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8081,http://127.0.0.1:8081",
    )
    return [origem.strip().rstrip("/") for origem in valor.split(",") if origem.strip()]
