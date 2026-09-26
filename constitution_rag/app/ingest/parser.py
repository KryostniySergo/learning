# app/ingest/parser.py
"""Разбор подготовленного текста Конституции в список структурных единиц.

Ожидаемый формат (его даёт scripts/prepare_source.py):
    Раздел первый
    Глава 1. ОСНОВЫ КОНСТИТУЦИОННОГО СТРОЯ
    Статья 67.1
    1. Текст части...
    2.1. Текст составной части...
    а) подпункт — остаётся внутри текста своей части
    Раздел второй. Заключительные и переходные положения
    1. Текст пункта...
Всё, что идёт до "Раздел первый", — преамбула.
"""

import re
from dataclasses import dataclass

RE_SECTION = re.compile(r"^Раздел (первый|второй)\b")
RE_CHAPTER = re.compile(r"^Глава (\d+)\. (.+)$")
RE_ARTICLE = re.compile(r"^Статья (\d+(?:\.\d+)?)$")
RE_PART = re.compile(r"^(\d+(?:\.\d+)?)\. (.+)$")


@dataclass(frozen=True)
class Unit:
    section: str | None  # "первый" / "второй"; None у преамбулы
    chapter: int | None
    chapter_title: str | None
    article: str | None  # "3", "67.1"; None у преамбулы и пунктов раздела второго
    part: str | None  # "1", "2.1"; None, если в статье нет нумерации частей
    text: str


def parse(text: str) -> list[Unit]:
    units: list[Unit] = []

    # текущее положение в документе
    section: str | None = None
    chapter: int | None = None
    chapter_title: str | None = None
    article: str | None = None
    part: str | None = None
    buf: list[str] = []  # строки текущей единицы

    def flush() -> None:
        """Сохранить накопленный текст как единицу с ТЕКУЩИМ состоянием."""
        nonlocal buf
        body = " ".join(buf).strip()
        if body:
            units.append(Unit(section, chapter, chapter_title, article, part, body))
        buf = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        if m := RE_SECTION.match(line):
            flush()
            section = m.group(1)
            chapter = chapter_title = article = part = None
        elif m := RE_CHAPTER.match(line):
            flush()
            chapter, chapter_title = int(m.group(1)), m.group(2).strip()
            article = part = None
        elif m := RE_ARTICLE.match(line):
            flush()
            article, part = m.group(1), None
        elif (article is not None or section == "второй") and (m := RE_PART.match(line)):
            # новая часть статьи или новый пункт раздела второго
            flush()
            part = m.group(1)
            buf = [m.group(2)]
        else:
            buf.append(line)  # продолжение текущей единицы: абзац, подпункт "а)", список

    flush()
    return units
