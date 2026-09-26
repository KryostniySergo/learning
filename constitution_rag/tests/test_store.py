# tests/test_store.py
import pytest
from app.ingest.chunker import Chunk
from app.search.store import ChromaStore


def make_chunk(cid: str, article: str, part: str | None, text: str) -> Chunk:
    """Минимальный чанк для тестов хранилища."""
    return Chunk(
        id=cid,
        embed_text=text,
        quote=text,
        ref=f"Статья {article}",
        chapter=1,
        chapter_title="ГЛАВА",
        article=article,
        part=part,
        kind="article",
    )


CHUNKS = [
    make_chunk("art-3-p-1", "3", "1", "власть народа"),
    make_chunk("art-3-p-2", "3", "2", "референдум"),
    make_chunk("art-10", "10", None, "разделение властей"),  # part=None -> не должен уронить Chroma
    make_chunk("art-3-p-2.1", "3", "2.1", "составная часть"),
]
VECTORS = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0.9, 0.1, 0, 0]]


@pytest.fixture
def store(tmp_path):
    """Пустое хранилище во временной папке."""
    return ChromaStore(tmp_path / "chroma", "test_collection")


def test_metric_is_cosine(store):
    """Коллекция создана с косинусной метрикой."""
    assert store.distance_space == "cosine"


def test_upsert_is_idempotent(store):
    """Повторная запись тех же чанков не меняет count."""
    store.upsert(CHUNKS, VECTORS)
    store.upsert(CHUNKS, VECTORS)
    assert store.count() == len(CHUNKS)


def test_search_returns_similarity(store):
    """Ближайший чанк первый, score = 1 - distance (для точного совпадения ≈ 1)."""
    store.upsert(CHUNKS, VECTORS)
    hits = store.search([1, 0, 0, 0], k=2)
    assert hits[0].id == "art-3-p-1"
    assert hits[0].score == pytest.approx(1.0, abs=1e-4)
    assert hits[0].score >= hits[1].score


def test_get_by_article_keeps_document_order(store):
    """Части статьи идут в порядке текста, а не в порядке id."""
    store.upsert(CHUNKS, VECTORS)
    assert [h.part for h in store.get_by_article("3")] == ["1", "2", "2.1"]
    assert store.get_by_article("999") == []


def test_part_none_is_restored_as_none(store):
    """Отфильтрованный None в метаданных возвращается как None."""
    store.upsert(CHUNKS, VECTORS)
    assert store.get_by_article("10")[0].part is None


def test_recreate_empties_collection(store):
    """recreate удаляет все записи."""
    store.upsert(CHUNKS, VECTORS)
    store.recreate()
    assert store.count() == 0
