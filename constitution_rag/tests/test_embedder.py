import numpy as np
import pytest
from app.search.embedder import Embedder


class FakeModel:
    """Притворяется SentenceTransformer: запоминает, что ему подали, и отдаёт единичные векторы."""

    def __init__(self) -> None:
        """Создаёт пустой журнал поданных текстов."""
        self.seen: list[str] = []

    def encode(self, texts, batch_size, normalize_embeddings, show_progress_bar):
        """Возвращает по вектору [1, 0, 0, 0] на каждый текст."""
        self.seen.extend(texts)
        return np.tile([1.0, 0.0, 0.0, 0.0], (len(texts), 1))

    def get_embedding_dimension(self) -> int:
        """Размерность фейковых векторов."""
        return 4


@pytest.fixture
def model():
    """Свежая фейковая модель для каждого теста."""
    return FakeModel()


def test_e5_prefixes(model):
    """Для e5 документы получают "passage: ", запросы — "query: " (с пробелом)."""
    emb = Embedder("intfloat/multilingual-e5-small", model=model)
    emb.embed_documents(["текст статьи"])
    emb.embed_query("кто источник власти")
    assert model.seen == ["passage: текст статьи", "query: кто источник власти"]


def test_no_prefixes_for_other_models(model):
    """Модели не из семейства e5 получают тексты без префиксов."""
    emb = Embedder("sentence-transformers/all-MiniLM-L6-v2", model=model)
    emb.embed_documents(["текст"])
    emb.embed_query("запрос")
    assert model.seen == ["текст", "запрос"]


def test_query_cache(model):
    """Повторный запрос (даже с другими пробелами) не вызывает модель."""
    emb = Embedder("intfloat/multilingual-e5-small", model=model)
    emb.embed_query("кто источник власти")
    emb.embed_query("  кто   источник власти ")
    assert len(model.seen) == 1


def test_cache_eviction(model):
    """При переполнении кеша вытесняется самый старый запрос."""
    emb = Embedder("intfloat/multilingual-e5-small", model=model, cache_size=2)
    for q in ["первый", "второй", "третий", "первый"]:
        emb.embed_query(q)
    assert len(model.seen) == 4  # "первый" вытеснен и посчитан заново


def test_cached_vector_cannot_be_corrupted(model):
    """Изменение возвращённого вектора не портит кеш."""
    emb = Embedder("intfloat/multilingual-e5-small", model=model)
    v = emb.embed_query("запрос")
    v[0] = 999.0
    assert emb.embed_query("запрос")[0] == 1.0


def test_dim(model):
    """dim берётся из модели."""
    assert Embedder("e5", model=model).dim == 4
