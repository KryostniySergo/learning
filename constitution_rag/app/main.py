import logging
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.deps import get_retriever, get_store
from app.schemas import Citation, SearchResponse
from app.search.embedder import Embedder
from app.search.retriever import Retriever
from app.search.store import ChromaStore

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Загружает тяжёлые объекты один раз при старте и освобождает при остановке.

    Всё до yield выполняется до приёма первого запроса, всё после — при выключении.
    """
    started = time.perf_counter()
    embedder = Embedder(settings.embedding_model, settings.embedding_device)
    store = ChromaStore(settings.chroma_path, settings.collection_name)
    app.state.embedder = embedder
    app.state.store = store
    app.state.retriever = Retriever(embedder, store, settings)
    logger.info("startup done in %.1f s, documents=%d", time.perf_counter() - started, store.count())
    yield
    app.state.retriever = app.state.store = app.state.embedder = None


app = FastAPI(title="Constitution RAG", version="0.2.0", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness: процесс жив и отвечает. Ничего тяжёлого не проверяем."""
    return {"status": "ok"}


@app.get("/readyz")
def readyz(store: Annotated[ChromaStore, Depends(get_store)]) -> dict[str, object]:
    """Readiness: сервис готов отвечать, то есть индекс построен и не пуст."""
    count = store.count()
    if count == 0:
        raise HTTPException(status_code=503, detail="Индекс пуст: запусти python -m scripts.ingest")
    return {"status": "ready", "documents": count, "collection": settings.collection_name}


@app.get("/search", response_model=SearchResponse)
async def search(
    retriever: Annotated[Retriever, Depends(get_retriever)],
    q: Annotated[str, Query(min_length=3, max_length=500, description="Вопрос на естественном языке")],
    k: Annotated[int, Query(ge=1, le=20, description="Сколько цитат вернуть")] = settings.default_k,
) -> SearchResponse:
    """Чистый поиск цитат без LLM: вопрос -> фрагменты Конституции со ссылками и скорами."""
    started = time.perf_counter()
    hits = await run_in_threadpool(retriever.retrieve, q, k)  # модель на CPU — не в event loop
    return SearchResponse(
        query=q,
        took_ms=int((time.perf_counter() - started) * 1000),
        collection=settings.collection_name,
        results=[Citation.from_hit(h) for h in hits],
    )
