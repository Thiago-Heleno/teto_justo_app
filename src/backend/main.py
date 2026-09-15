from fastapi import FastAPI
from routers import casa, pertencer, sessao, tarefa, usuario

app = FastAPI(title="Teto Justo API")

app.include_router(usuario.router)
app.include_router(tarefa.router)
app.include_router(casa.router)
app.include_router(sessao.router)
app.include_router(pertencer.router)


@app.get("/health")
def health():
    return {"status": "ok"}
