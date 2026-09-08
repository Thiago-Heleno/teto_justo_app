from fastapi import FastAPI

app = FastAPI(title="Teto Justo API")

@app.get("/health")
def health():
    return {"status": "ok"}