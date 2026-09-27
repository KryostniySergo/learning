import logging
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Query
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.deps import get_llm, get_retriever, get_store
from app.llm.client import LLMClient, OpenAICompatibleClient
from app.llm.rag import generate_answer
from app.schemas import ArticleResponse, AskRequest, AskResponse, Citation, SearchResponse
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
    embedder = Embedder.from_settings(settings)
    store = ChromaStore(settings.chroma_path, settings.collection_name)
    app.state.embedder = embedder
    app.state.store = store
    app.state.retriever = Retriever(embedder, store, settings)
    app.state.llm = (
        OpenAICompatibleClient(settings.llm_model, settings.llm_api_key, settings.llm_base_url, settings.llm_timeout)
        if settings.llm_enabled
        else None
    )
    logger.info("startup done in %.1f s, documents=%d", time.perf_counter() - started, store.count())
    yield
    app.state.llm = app.state.retriever = app.state.store = app.state.embedder = None


app = FastAPI(title="Constitution RAG", version="0.3.0", lifespan=lifespan)

NOT_FOUND_MESSAGE = "В тексте Конституции РФ прямого ответа на этот вопрос не нашлось."
NO_LLM_MESSAGE = "Связный ответ сейчас недоступен — ниже найденные фрагменты текста."


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


@app.get("/articles/{number}", response_model=ArticleResponse)
def get_article(
    store: Annotated[ChromaStore, Depends(get_store)],
    number: Annotated[str, Path(pattern=r"^\d{1,3}(\.\d)?$", examples=["3", "67.1"])],
) -> ArticleResponse:
    """Точная выборка статьи по номеру: фильтр по метаданным, без векторного поиска."""
    hits = store.get_by_article(number)
    if not hits:
        raise HTTPException(status_code=404, detail=f"Статья {number} не найдена")
    return ArticleResponse(
        article=number,
        parts=[Citation.from_hit(h) for h in hits],
    )


@app.post("/ask", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    retriever: Annotated[Retriever, Depends(get_retriever)],
    llm: Annotated[LLMClient | None, Depends(get_llm)],
) -> AskResponse:
    """Ответ на вопрос: цитаты из Конституции и (если доступна LLM) связный пересказ.

    Сервис не падает из-за LLM: если она выключена или недоступна, возвращаются цитаты.
    """
    started = time.perf_counter()

    def elapsed() -> int:
        """Миллисекунды с начала обработки запроса."""
        return int((time.perf_counter() - started) * 1000)

    hits = await run_in_threadpool(retriever.retrieve, payload.question, payload.k)
    if not hits:  # порог сработал — LLM не вызываем вообще
        return AskResponse(found=False, message=NOT_FOUND_MESSAGE, citations=[], llm_used=False, took_ms=elapsed())

    citations = [Citation.from_hit(h) for h in hits]  # ЦИТАТЫ ВСЕГДА ИЗ БД
    if llm is None:
        return AskResponse(found=True, message=NO_LLM_MESSAGE, citations=citations, llm_used=False, took_ms=elapsed())

    result = await run_in_threadpool(generate_answer, payload.question, hits, llm, settings.llm_max_tokens)
    if result.status == "ok":
        return AskResponse(found=True, answer=result.text, citations=citations, llm_used=True, took_ms=elapsed())
    if result.status == "not_found":
        return AskResponse(
            found=False, message=NOT_FOUND_MESSAGE, citations=citations, llm_used=True, took_ms=elapsed()
        )
    # error / bad_citations: ответа модели нет или ему нельзя доверять — отдаём только цитаты
    return AskResponse(found=True, message=NO_LLM_MESSAGE, citations=citations, llm_used=False, took_ms=elapsed())
