# app/main.py
"""FastAPI-приложение: жизненный цикл, middleware и эндпоинты."""

import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Query
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.deps import get_llm, get_retriever, get_store
from app.llm.client import LLMClient, OpenAICompatibleClient
from app.llm.rag import PROMPT_VERSION, generate_answer
from app.middleware import RateLimiter, rate_limit_middleware, request_context_middleware
from app.observability import Stopwatch, log_event, setup_logging
from app.schemas import ArticleResponse, AskRequest, AskResponse, Citation, SearchResponse
from app.search.embedder import Embedder
from app.search.retriever import Retriever
from app.search.store import ChromaStore, Hit
from app.security import looks_like_injection, sanitize_question

setup_logging(settings.log_level)
logger = logging.getLogger("app")

NOT_FOUND_MESSAGE = "В тексте Конституции РФ прямого ответа на этот вопрос не нашлось."
LLM_DISABLED_MESSAGE = "Генерация ответов выключена — ниже найденные фрагменты текста."
LLM_FAILED_MESSAGE = "Не удалось получить связный ответ — ниже найденные фрагменты текста."


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Загружает тяжёлые объекты один раз при старте и освобождает при остановке."""
    with Stopwatch() as sw:
        embedder = Embedder.from_settings(settings)
        store = ChromaStore(settings.chroma_path, settings.collection_name)
        app.state.embedder = embedder
        app.state.store = store
        app.state.retriever = Retriever(embedder, store, settings)
        app.state.llm = (
            OpenAICompatibleClient(
                settings.llm_model, settings.llm_api_key, settings.llm_base_url, settings.llm_timeout
            )
            if settings.llm_enabled
            else None
        )
    log_event(
        logger,
        "startup",
        took_ms=sw.ms,
        documents=store.count(),
        collection=settings.collection_name,
        model=settings.embedding_model,
        hybrid=settings.use_hybrid,
        min_score=settings.min_score,
        llm=f"{settings.llm_model} @ {settings.llm_base_url}" if settings.llm_enabled else "disabled",
        rate_limit_per_minute=settings.rate_limit_per_minute,
    )
    yield
    app.state.llm = app.state.retriever = app.state.store = app.state.embedder = None


app = FastAPI(title="Constitution RAG", version="0.4.0", lifespan=lifespan)
app.state.rate_limiter = RateLimiter(settings.rate_limit_per_minute)

# Порядок важен: middleware, добавленный ПОЗЖЕ, оборачивает более ранние и выполняется ПЕРВЫМ.
# Так request_id назначается раньше всего, и даже ответ 429 получает id и строку в логе.
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(request_context_middleware)


def _clean_question(text: str) -> str:
    """Санитизация вопроса; если после неё почти ничего не осталось — 422."""
    cleaned = sanitize_question(text)
    if len(cleaned) < 3:
        raise HTTPException(status_code=422, detail="Вопрос пуст после очистки служебной разметки")
    return cleaned


def _hits_for_log(hits: list[Hit]) -> list[dict]:
    """Краткое описание найденных фрагментов для лога: id и скор, без текста."""
    return [{"id": h.id, "score": round(h.score, 4), "match": h.source} for h in hits]


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness: процесс жив и отвечает. Ничего тяжёлого не проверяем."""
    return {"status": "ok"}


@app.get("/readyz")
def readyz(
    store: Annotated[ChromaStore, Depends(get_store)],
    llm: Annotated[LLMClient | None, Depends(get_llm)],
) -> dict[str, object]:
    """Readiness: индекс построен и не пуст. Заодно показывает, включена ли генерация."""
    count = store.count()
    if count == 0:
        raise HTTPException(status_code=503, detail="Индекс пуст: запусти python -m scripts.ingest")
    return {
        "status": "ready",
        "documents": count,
        "collection": settings.collection_name,
        "llm": f"{settings.llm_model} @ {settings.llm_base_url}" if llm else "disabled",
    }


@app.get("/search", response_model=SearchResponse)
async def search(
    retriever: Annotated[Retriever, Depends(get_retriever)],
    q: Annotated[str, Query(min_length=3, max_length=500, description="Вопрос на естественном языке")],
    k: Annotated[int, Query(ge=1, le=20, description="Сколько цитат вернуть")] = settings.default_k,
) -> SearchResponse:
    """Чистый поиск цитат без LLM: вопрос -> фрагменты Конституции со ссылками и скорами."""
    query = _clean_question(q)
    trace: dict = {}
    with Stopwatch() as total:
        hits = await run_in_threadpool(retriever.retrieve, query, k, trace)
    log_event(logger, "search", query=query, k=k, hits=_hits_for_log(hits), total_ms=total.ms, **trace)
    return SearchResponse(
        query=query,
        took_ms=total.ms,
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
    return ArticleResponse(article=number, parts=[Citation.from_hit(h) for h in hits])


@app.post("/ask", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    retriever: Annotated[Retriever, Depends(get_retriever)],
    llm: Annotated[LLMClient | None, Depends(get_llm)],
) -> AskResponse:
    """Ответ на вопрос: цитаты из Конституции и (если доступна LLM) связный пересказ.

    Сервис не падает из-за LLM: если она выключена или недоступна, возвращаются цитаты.
    Каждый запрос пишет в лог событие "ask", по которому видно, что именно увидела модель.
    """
    question = _clean_question(payload.question)
    trace: dict = {}
    event: dict = {
        "question": question,
        "k": payload.k,
        "suspicious": looks_like_injection(question),
        "prompt_version": PROMPT_VERSION,
    }

    with Stopwatch() as total:
        hits = await run_in_threadpool(retriever.retrieve, question, payload.k, trace)
        event["hits"] = _hits_for_log(hits)

        if not hits:  # порог сработал — LLM не вызываем вообще
            event["llm_status"] = "skipped"
            response = AskResponse(found=False, message=NOT_FOUND_MESSAGE, citations=[], llm_used=False, took_ms=0)
        elif llm is None:
            event["llm_status"] = "disabled"
            response = AskResponse(
                found=True,
                message=LLM_DISABLED_MESSAGE,
                citations=[Citation.from_hit(h) for h in hits],
                llm_used=False,
                took_ms=0,
            )
        else:
            with Stopwatch() as llm_sw:
                result = await run_in_threadpool(generate_answer, question, hits, llm, settings.llm_max_tokens)
            event.update(llm_status=result.status, llm_ms=llm_sw.ms, answer=result.text)
            response = _ask_response(result.status, result.text, hits)

    response.took_ms = total.ms
    log_event(logger, "ask", found=response.found, total_ms=total.ms, **trace, **event)
    return response


def _ask_response(status: str, text: str | None, hits: list[Hit]) -> AskResponse:
    """Собирает ответ /ask по статусу генерации. Цитаты всегда берутся из БД."""
    citations = [Citation.from_hit(h) for h in hits]
    if status == "ok":
        return AskResponse(found=True, answer=text, citations=citations, llm_used=True, took_ms=0)
    if status == "not_found":
        return AskResponse(found=False, message=NOT_FOUND_MESSAGE, citations=citations, llm_used=True, took_ms=0)
    # error / bad_citations: ответа модели нет или ему нельзя доверять — отдаём только цитаты
    return AskResponse(found=True, message=LLM_FAILED_MESSAGE, citations=citations, llm_used=False, took_ms=0)
