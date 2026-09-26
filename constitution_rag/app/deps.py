from fastapi import Request

from app.search.retriever import Retriever
from app.search.store import ChromaStore


def get_store(request: Request) -> ChromaStore:
    """Хранилище, созданное при старте приложения."""
    return request.app.state.store


def get_retriever(request: Request) -> Retriever:
    """Ретривер, созданный при старте приложения."""
    return request.app.state.retriever
