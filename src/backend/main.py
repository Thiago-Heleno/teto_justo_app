from fastapi import FastAPI
from routers import casa, tarefa, usuario

app = FastAPI(title="Teto Justo API")

app.include_router(usuario.router)
app.include_router(tarefa.router)
app.include_router(casa.router)


@app.get("/health")
def health():
    return {"status": "ok"}
