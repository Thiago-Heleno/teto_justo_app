from fastapi import FastAPI
from routers import tasks, usuario

app = FastAPI(title="Teto Justo API")

app.include_router(usuario.router)
app.include_router(tasks.router)


@app.get("/health")
def health():
    return {"status": "ok"}
