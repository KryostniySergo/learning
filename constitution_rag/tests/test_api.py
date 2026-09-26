# tests/test_api.py
import pytest
from app.main import app
from app.search.store import Hit
from fastapi.testclient import TestClient

HITS = [
    Hit(
        id="art-3-p-1..2",
        quote="Носителем суверенитета...",
        ref="Статья 3, части 1-2",
        article="3",
        part="1",
        score=0.91234,
    ),
    Hit(id="art-10", quote="Государственная власть...", ref="Статья 10", article="10", part=None, score=0.84),
]


class FakeRetriever:
    """Возвращает заранее заданные фрагменты и запоминает запросы."""

    def __init__(self, hits: list[Hit]) -> None:
        """Сохраняет фрагменты, которые будет отдавать."""
        self.hits = hits
        self.calls: list[tuple[str, int]] = []

    def retrieve(self, query: str, k: int) -> list[Hit]:
        """Первые k заготовленных фрагментов."""
        self.calls.append((query, k))
        return self.hits[:k]


class FakeStore:
    """Хранилище, у которого есть только count()."""

    def __init__(self, count: int) -> None:
        """Задаёт, сколько документов «лежит» в хранилище."""
        self._count = count

    def count(self) -> int:
        """Число документов."""
        return self._count


@pytest.fixture
def client():
    """Клиент без lifespan: вместо настоящей модели и Chroma подкладываем фейки."""
    app.state.retriever = FakeRetriever(HITS)
    app.state.store = FakeStore(count=len(HITS))
    return TestClient(app)  # без with — lifespan не запускается


def test_search_ok(client):
    """/search возвращает цитаты в формате API."""
    r = client.get("/search", params={"q": "кто источник власти", "k": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["results"][0]["ref"] == "Статья 3, части 1-2"
    assert body["results"][0]["score"] == 0.9123  # округление до 4 знаков
    assert body["results"][1]["part"] is None
    assert body["took_ms"] >= 0


def test_search_passes_k(client):
    """k из запроса доходит до ретривера."""
    client.get("/search", params={"q": "кто источник власти", "k": 1})
    assert app.state.retriever.calls == [("кто источник власти", 1)]


@pytest.mark.parametrize("params", [{"q": "ab"}, {"q": "x" * 501}, {"q": "норм", "k": 0}, {"q": "норм", "k": 21}])
def test_search_validation(client, params):
    """Слишком короткий/длинный q и k вне 1..20 -> 422."""
    assert client.get("/search", params=params).status_code == 422


def test_readyz(client):
    """readyz: 200 при непустом индексе, 503 при пустом."""
    assert client.get("/readyz").status_code == 200
    app.state.store = FakeStore(count=0)
    assert client.get("/readyz").status_code == 503


class ArticleStore(FakeStore):
    """Хранилище с точной выборкой по статье."""

    def get_by_article(self, article: str) -> list[Hit]:
        """Фрагменты из HITS с нужным номером статьи."""
        return [h for h in HITS if h.article == article]


def test_article_found(client):
    """/articles/3 отдаёт части статьи без скоров."""
    app.state.store = ArticleStore(count=len(HITS))
    r = client.get("/articles/3")
    assert r.status_code == 200
    body = r.json()
    assert body["article"] == "3"
    assert body["parts"][0]["ref"] == "Статья 3, части 1-2"
    assert body["parts"][0]["score"] is None


def test_article_not_found(client):
    """Несуществующая статья -> 404."""
    app.state.store = ArticleStore(count=len(HITS))
    assert client.get("/articles/999").status_code == 404


@pytest.mark.parametrize("number", ["abc", "3.", "67.12", "1234", "-1"])
def test_article_bad_number(client, number):
    """Строка, не похожая на номер статьи -> 422."""
    app.state.store = ArticleStore(count=len(HITS))
    assert client.get(f"/articles/{number}").status_code == 422
