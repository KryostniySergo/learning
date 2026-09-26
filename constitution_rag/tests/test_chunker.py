# tests/test_chunker.py
import pytest
from app.ingest.chunker import build_chunks
from app.ingest.parser import Unit, parse

from tests.parser_test import FIXTURE

MIN, MAX = 200, 900


@pytest.fixture
def chunks():
    return build_chunks(parse(FIXTURE), MIN, MAX)


def art(article: str, part: str | None, text: str) -> Unit:
    return Unit("первый", 1, "ОСНОВЫ КОНСТИТУЦИОННОГО СТРОЯ", article, part, text)


def test_ids_are_unique(chunks):
    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids))


def test_build_is_deterministic():
    units = parse(FIXTURE)
    assert build_chunks(units, MIN, MAX) == build_chunks(units, MIN, MAX)


def test_prefix_only_in_embed_text(chunks):
    c = next(c for c in chunks if c.article == "10")
    assert c.embed_text.startswith("Глава 1. Основы конституционного строя. Статья 10. ")
    assert c.quote.startswith("Государственная власть")
    assert "Глава" not in c.quote


def test_short_parts_are_merged_with_ref_range():
    units = [art("5", "1", "а" * 50), art("5", "2", "б" * 50), art("5", "3", "в" * 300)]
    chunks = build_chunks(units, MIN, MAX)
    first = chunks[0]
    assert first.ref == "Статья 5, части 1-3"
    assert first.id == "art-5-p-1..3"
    assert first.quote == f"{'а' * 50} {'б' * 50} {'в' * 300}"  # склейка через пробел


def test_merge_never_crosses_article_boundary():
    units = [art("5", "1", "короткая часть"), art("6", "1", "другая статья")]
    assert [c.article for c in build_chunks(units, MIN, MAX)] == ["5", "6"]


def test_long_unit_is_split_with_overlap():
    sentences = [f"Предложение номер {i} " + "слово " * 40 + "." for i in range(10)]
    chunks = build_chunks([art("72", "1", " ".join(sentences))], MIN, MAX)
    assert len(chunks) > 1
    assert all(len(c.quote) <= MAX for c in chunks)
    assert [c.id for c in chunks] == [f"art-72-p-1-c{i}" for i in range(1, len(chunks) + 1)]
    last_sentence_of_first = chunks[0].quote.split(" Предложение")[-1]
    assert last_sentence_of_first in chunks[1].quote  # перекрытие


def test_refs_for_special_units(chunks):
    refs = {c.kind: c.ref for c in chunks}
    assert refs["preamble"] == "Преамбула"
    assert "Раздел второй, пункт 1" in [c.ref for c in chunks if c.kind == "transitional"]


def test_length_bounds(chunks):
    by_article: dict[str | None, list] = {}
    for c in chunks:
        by_article.setdefault(c.article, []).append(c)
    for article, group in by_article.items():
        if article is None:
            continue
        # короче MIN может быть только последний чанк статьи
        assert all(len(c.quote) >= MIN for c in group[:-1]), article
