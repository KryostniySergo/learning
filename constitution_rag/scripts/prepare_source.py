# scripts/prepare_source.py
"""Одноразовая подготовка исходника: сырой текст -> чистый текст для парсера.

Запуск:  python -m scripts.prepare_source
Читает   data/raw/constitution.txt
Пишет    data/raw/constitution_clean.txt

Исходный файл не трогаем: если скачаешь новую редакцию, просто запусти скрипт заново.
"""

import re
from pathlib import Path

from app.ingest.loader import load_text

SRC = Path("data/raw/constitution.txt")
DST = Path("data/raw/constitution_clean.txt")

MAX_ARTICLE = 137

# --- 1. Шапка до преамбулы (заголовок, список редакций) нам не нужна ---
PREAMBLE_START = "Мы, многонациональный народ"

# --- 2. Редакционные пометки: "(В редакции ...)", "(Дополнение частью - ...)" и т.п. ---
# Это не текст нормы, а история поправок. В цитатах и в эмбеддингах они только мешают.
RE_EDITORIAL = re.compile(
    r"\s*\((?:В редакции|Дополнение|Статья в редакции|Часть в редакции|"
    r"Наименование в редакции|Закон Российской Федерации о поправке)[^()]*\)"
)

# --- 3. Разделы и главы: собираем заголовок в одну строку ---
RE_SECTION = re.compile(r"^РАЗДЕЛ (ПЕРВЫЙ|ВТОРОЙ)$", re.MULTILINE)
RE_CHAPTER = re.compile(r"^ГЛАВА (\d+)\n+(.+)$", re.MULTILINE)
RE_SECTION_TWO_TITLE = re.compile(r"^(Раздел второй)\n+(Заключительные и переходные положения)$", re.MULTILINE)

# --- 4. Составные номера статей: "Статья 671" -> "Статья 67.1" ---
RE_ARTICLE_SUP = re.compile(r"^(Статья )(\d{2,3})1$", re.MULTILINE)

# --- 5. Составные подпункты: "ж1)" -> "ж.1)", и ссылки на них: пункт "д1" -> пункт "д.1" ---
RE_SUBITEM_SUP = re.compile(r"^([а-я])(\d)\)", re.MULTILINE)
RE_SUBITEM_REF = re.compile(r'"([а-я])(\d)"')

# --- 6. Составные части: "21." после части "2." -> "2.1." ---
RE_ARTICLE_LINE = re.compile(r"^Статья \d+(?:\.\d+)?$")
RE_PART_LINE = re.compile(r"^(\d+)\. ")


def strip_header(text: str) -> str:
    pos = text.find(PREAMBLE_START)
    if pos == -1:
        raise ValueError(f"Не найдено начало преамбулы: {PREAMBLE_START!r}")
    return text[pos:]


def fix_articles(text: str) -> str:
    def repl(m: re.Match) -> str:
        if int(m.group(2) + "1") <= MAX_ARTICLE:  # "Статья 11", "Статья 131" — настоящие
            return m.group(0)
        return f"{m.group(1)}{m.group(2)}.1"

    return RE_ARTICLE_SUP.sub(repl, text)


def fix_compound_parts(text: str) -> str:
    """Часть N.1 при копировании превращается в "N1.". Отличаем её от обычной части так:
    номер равен предыдущий*10 + 1 внутри той же статьи (после 2 идёт 21, после 1 — 11).
    Статей с 11+ частями в Конституции нет, поэтому правило однозначно."""
    out: list[str] = []
    prev_part: int | None = None
    for line in text.split("\n"):
        if RE_ARTICLE_LINE.match(line) or line.startswith(("Глава ", "Раздел ")):
            prev_part = None  # новая статья — счёт частей заново
        elif m := RE_PART_LINE.match(line):
            num = int(m.group(1))
            if prev_part is not None and num == prev_part * 10 + 1:
                line = f"{prev_part}.1. {line[m.end() :]}"
                # prev_part не меняем: следующая часть будет prev_part + 1
            else:
                prev_part = num
        out.append(line)
    return "\n".join(out)


def prepare(raw: str) -> str:
    text = strip_header(raw)
    text = RE_EDITORIAL.sub("", text)
    text = RE_SECTION.sub(lambda m: f"Раздел {m.group(1).lower()}", text)
    text = RE_SECTION_TWO_TITLE.sub(r"\1. \2", text)
    text = RE_CHAPTER.sub(lambda m: f"Глава {m.group(1)}. {m.group(2).strip()}", text)
    text = fix_articles(text)
    text = RE_SUBITEM_SUP.sub(r"\1.\2)", text)
    text = RE_SUBITEM_REF.sub(r'"\1.\2"', text)
    text = fix_compound_parts(text)
    # после удаления пометок остаются пустые строки и хвостовые пробелы
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def report(text: str) -> None:
    lines = text.split("\n")
    articles = [l for l in lines if RE_ARTICLE_LINE.match(l)]
    numbers = {l.split()[1] for l in articles}
    missing = [n for n in range(1, MAX_ARTICLE + 1) if str(n) not in numbers]
    print(f"строк: {len(lines)}, символов: {len(text)}")
    print(f"статей: {len(articles)}, пропущены: {missing or 'нет'}")
    print("составные статьи:", sorted((n for n in numbers if "." in n), key=float))
    print("главы:", [l for l in lines if l.startswith("Глава ")])
    print("разделы:", [l for l in lines if l.startswith("Раздел ")])
    print("составные части:", [l[:40] for l in lines if re.match(r"^\d+\.1\. ", l)])
    print("составные подпункты:", sorted({l[:4] for l in lines if re.match(r"^[а-я]\.\d\)", l)}))
    leftovers = [l[:60] for l in lines if "редакции" in l or "Дополнение" in l]
    print("остались редакционные пометки:", leftovers or "нет")


if __name__ == "__main__":
    clean = prepare(load_text(SRC))
    DST.write_text(clean, encoding="utf-8")
    report(clean)
    print(f"\nзаписано в {DST}")
