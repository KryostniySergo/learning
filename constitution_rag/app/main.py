from fastapi import FastAPI

from app.config import settings

app = FastAPI(title="Constitution RAG", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness: процесс жив и отвечает. Ничего тяжёлого здесь не проверяем."""
    return {"status": "ok", "collection": settings.collection_name}
