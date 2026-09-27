from fastapi import Request

from app.llm.client import LLMClient
from app.search.retriever import Retriever
from app.search.store import ChromaStore


def get_store(request: Request) -> ChromaStore:
    """Хранилище, созданное при старте приложения."""
    return request.app.state.store


def get_retriever(request: Request) -> Retriever:
    """Ретривер, созданный при старте приложения."""
    return request.app.state.retriever


def get_llm(request: Request) -> LLMClient | None:
    """LLM-клиент или None, если генерация выключена."""
    return getattr(request.app.state, "llm", None)
