from types import SimpleNamespace

import pytest
from app.search.retriever import Retriever, rrf
from app.search.store import Hit


def hit(cid: str, article: str, quote: str, score: float = 0.0, source: str = "vector") -> Hit:
    """Короткий конструктор Hit для тестов."""
    return Hit(id=cid, quote=quote, ref=f"Статья {article}", article=article, part=None, score=score, source=source)


CORPUS = [
    hit("art-15", "15", "Конституция имеет высшую юридическую силу"),
    hit("art-25", "25", "Жилище неприкосновенно"),
    hit("art-81", "81", "Президент избирается сроком на шесть лет"),
]


class FakeEmbedder:
    """Не считает векторы, а только запоминает, что его вызывали."""

    def __init__(self) -> None:
        """Пустой журнал вызовов."""
        self.calls: list[str] = []

    def embed_query(self, text: str) -> list[float]:
        """Возвращает фиктивный вектор."""
        self.calls.append(text)
        return [1.0, 0.0]


class FakeStore:
    """Хранилище, у которого векторный поиск возвращает заранее заданных кандидатов."""

    def __init__(self, corpus: list[Hit], candidates: list[Hit]) -> None:
        """corpus — всё содержимое (для BM25 и выборок), candidates — ответ векторного поиска."""
        self.corpus = corpus
        self.candidates = candidates

    def count(self) -> int:
        """Сколько фрагментов в хранилище."""
        return len(self.corpus)

    def all_chunks(self) -> list[Hit]:
        """Всё содержимое."""
        return self.corpus

    def search(self, vector, k, where=None) -> list[Hit]:
        """Заготовленные кандидаты векторного поиска."""
        return self.candidates[:k]

    def get_by_ids(self, ids, vector=None) -> dict[str, Hit]:
        """Фрагменты по id; "векторный" скор фиксированный."""
        return {h.id: hit(h.id, h.article, h.quote, score=0.7) for h in self.corpus if h.id in ids}

    def get_by_article(self, article: str) -> list[Hit]:
        """Точная выборка по номеру статьи."""
        return [hit(h.id, h.article, h.quote, source="exact") for h in self.corpus if h.article == article]


def make_settings(**overrides) -> SimpleNamespace:
    """Настройки ретривера с возможностью переопределить отдельные поля."""
    base = dict(candidate_k=30, min_score=0.8, use_hybrid=True, bm25_stemming=True, rrf_k=60)
    return SimpleNamespace(**(base | overrides))


def test_rrf_prefers_documents_high_in_both_lists():
    """Документ на 2-м месте в обоих списках обгоняет лидера только одного списка."""
    assert rrf([["a", "b", "c"], ["d", "b", "e"]])[0] == "b"


def test_below_threshold_returns_nothing():
    """Если лучший векторный кандидат ниже min_score — пустой ответ."""
    store = FakeStore(CORPUS, [hit("art-25", "25", "Жилище неприкосновенно", score=0.75)])
    r = Retriever(FakeEmbedder(), store, make_settings())
    assert r.retrieve("как приготовить борщ", 5) == []


def test_article_mention_uses_exact_lookup_without_embedding():
    """ "статья 15" -> точная выборка, модель эмбеддингов не вызывается."""
    embedder = FakeEmbedder()
    r = Retriever(embedder, FakeStore(CORPUS, []), make_settings())
    hits = r.retrieve("что говорит статья 15", 5)
    assert [h.article for h in hits] == ["15"]
    assert hits[0].source == "exact"
    assert embedder.calls == []


def test_unknown_article_falls_back_to_search():
    """Несуществующая "статья 999" не ломает поиск, а переходит к обычному ретриву."""
    store = FakeStore(CORPUS, [hit("art-25", "25", "Жилище неприкосновенно", score=0.9)])
    r = Retriever(FakeEmbedder(), store, make_settings())
    hits = r.retrieve("статья 999 про жилище", 5)
    assert hits and hits[0].id == "art-25"
    assert all(h.source != "exact" for h in hits)


def test_hybrid_adds_lexical_only_hits():
    """Фрагмент, который нашёл только BM25, попадает в выдачу с пометкой lexical."""
    candidates = [hit("art-15", "15", CORPUS[0].quote, score=0.85)]
    r = Retriever(FakeEmbedder(), FakeStore(CORPUS, candidates), make_settings())
    hits = r.retrieve("срок полномочий президента", 5)
    by_id = {h.id: h for h in hits}
    assert by_id["art-81"].source == "lexical"
    assert by_id["art-81"].score == 0.7  # скор досчитан, а не нулевой
    assert by_id["art-15"].source == "vector"


def test_without_hybrid_returns_vector_candidates():
    """use_hybrid=False: ровно векторные кандидаты, без BM25."""
    candidates = [hit("art-15", "15", CORPUS[0].quote, score=0.85)]
    r = Retriever(FakeEmbedder(), FakeStore(CORPUS, candidates), make_settings(use_hybrid=False))
    assert [h.id for h in r.retrieve("срок полномочий президента", 5)] == ["art-15"]


def test_bm25_is_built_lazily_when_store_was_empty():
    """Если при старте индекс был пуст, BM25 строится при первом запросе после ingest."""
    store = FakeStore([], [])
    r = Retriever(FakeEmbedder(), store, make_settings())
    store.corpus = CORPUS
    store.candidates = [hit("art-15", "15", CORPUS[0].quote, score=0.85)]
    assert "art-81" in [h.id for h in r.retrieve("срок полномочий президента", 5)]


@pytest.mark.parametrize("k", [1, 2])
def test_respects_k(k):
    """Возвращается не больше k фрагментов."""
    candidates = [hit(h.id, h.article, h.quote, score=0.9) for h in CORPUS]
    r = Retriever(FakeEmbedder(), FakeStore(CORPUS, candidates), make_settings())
    assert len(r.retrieve("президент жилище конституция", k)) == k
