# app/main.py
from app.config import settings
from fastapi import FastAPI

app = FastAPI(title="Constitution RAG", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "collection": settings.collection_name}
