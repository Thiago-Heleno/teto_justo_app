from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import origens_frontend
from routers import casa, jobs, pertencer, rotatividade, sessao, tarefa, usuario

app = FastAPI(title="Teto Justo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origens_frontend(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "X-Session-Transport"],
)

app.include_router(usuario.router)
app.include_router(jobs.router)
app.include_router(tarefa.router)
app.include_router(rotatividade.router)
app.include_router(casa.router)
app.include_router(sessao.router)
app.include_router(pertencer.router)


@app.get("/health")
def health():
    return {"status": "ok"}
