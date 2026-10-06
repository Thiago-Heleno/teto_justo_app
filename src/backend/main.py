import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import casa, jobs, pertencer, rotatividade, sessao, tarefa, usuario

app = FastAPI(title="Teto Justo API")

origens_frontend = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:8081,http://127.0.0.1:8081",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origens_frontend,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Retry-After"],
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
