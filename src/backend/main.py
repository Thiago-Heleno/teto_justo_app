from fastapi import FastAPI
from routers import usuario

app = FastAPI(title="Teto Justo API")

app.include_router(usuario.router)


@app.get("/health")
def health():
    return {"status": "ok"}
