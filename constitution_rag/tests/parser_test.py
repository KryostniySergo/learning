# tests/test_parser.py
from pathlib import Path

import pytest
from app.ingest.loader import load_text
from app.ingest.parser import parse

FIXTURE = """\
Мы, многонациональный народ Российской Федерации,
принимаем КОНСТИТУЦИЮ РОССИЙСКОЙ ФЕДЕРАЦИИ.

Раздел первый

Глава 1. ОСНОВЫ КОНСТИТУЦИОННОГО СТРОЯ

Статья 3

1. Носителем суверенитета и единственным источником власти в Российской Федерации является ее многонациональный народ.
2. Народ осуществляет свою власть непосредственно.
3. Высшим непосредственным выражением власти народа являются референдум и свободные выборы.
4. Никто не может присваивать власть в Российской Федерации.

Статья 10

Государственная власть в Российской Федерации осуществляется на основе разделения на законодательную, исполнительную и судебную.

Глава 3. ФЕДЕРАТИВНОЕ УСТРОЙСТВО

Статья 67

1. Территория Российской Федерации включает в себя территории ее субъектов.
2. Российская Федерация обладает суверенными правами.
2.1. Российская Федерация обеспечивает защиту своего суверенитета.
3. Границы между субъектами могут быть изменены.

Статья 67.1

1. Российская Федерация является правопреемником Союза ССР.

Статья 71

В ведении Российской Федерации находятся:
а) принятие и изменение Конституции Российской Федерации;
б) федеративное устройство и территория Российской Федерации;

Раздел второй. Заключительные и переходные положения

1. Конституция Российской Федерации вступает в силу со дня официального ее опубликования.
День всенародного голосования 12 декабря 1993 г. считается днем принятия Конституции.
2. Законы применяются в части, не противоречащей Конституции.
"""


@pytest.fixture
def units():
    return parse(FIXTURE)


def by_article(units, article):
    return [u for u in units if u.article == article]


def test_preamble_is_first_unit_without_structure(units):
    first = units[0]
    assert first.text.startswith("Мы, многонациональный народ")
    assert (first.section, first.chapter, first.article, first.part) == (None, None, None, None)


def test_article_3_has_four_parts(units):
    parts = [u.part for u in by_article(units, "3")]
    assert parts == ["1", "2", "3", "4"]


def test_article_without_parts_is_single_unit(units):
    art10 = by_article(units, "10")
    assert len(art10) == 1 and art10[0].part is None


def test_compound_article_and_part(units):
    assert [u.part for u in by_article(units, "67")] == ["1", "2", "2.1", "3"]
    assert by_article(units, "67.1"), "составной номер статьи потерян"


def test_subitems_stay_inside_their_unit(units):
    art71 = by_article(units, "71")
    assert len(art71) == 1
    assert "а) принятие" in art71[0].text and "б) федеративное" in art71[0].text


def test_chapter_is_set_for_every_article(units):
    assert all(u.chapter is not None for u in units if u.article)
    assert by_article(units, "67.1")[0].chapter == 3


def test_section_two_points(units):
    points = [u for u in units if u.section == "второй"]
    assert [u.part for u in points] == ["1", "2"]
    assert all(u.article is None and u.chapter is None for u in points)
    assert "День всенародного голосования" in points[0].text  # продолжение пункта 1


def test_no_empty_text(units):
    assert all(u.text.strip() for u in units)


# --- проверка на настоящем файле: пропускается, если исходника нет (например, в CI) ---
SOURCE = Path("data/raw/constitution.txt")


@pytest.mark.skipif(not SOURCE.exists(), reason="нет исходника Конституции")
def test_real_source_has_all_articles():
    units = parse(load_text(SOURCE))
    articles = {u.article for u in units if u.article}
    missing = [n for n in range(1, 138) if str(n) not in articles]
    assert missing == [], f"пропущены статьи: {missing}"
    assert {"67.1", "75.1", "79.1", "92.1", "103.1"} <= articles
    assert [u.part for u in units if u.article == "3"] == ["1", "2", "3", "4"]
    assert all(u.chapter is not None for u in units if u.article)
    assert all(u.text.strip() for u in units)
