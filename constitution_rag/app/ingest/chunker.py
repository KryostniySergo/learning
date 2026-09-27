# app/ingest/chunker.py
"""Units -> Chunks: слияние коротких частей, разрезание длинных, стабильные id."""

import re
from dataclasses import dataclass

from app.ingest.parser import Unit

# Граница предложения: после . ; : идёт пробел, а за ним заглавная буква, кавычка,
# скобка или подпункт вида "а)" / "ж.1)". "1993 г. считается" не режется: дальше строчная.
RE_SENTENCE = re.compile(r"(?<=[.;:])\s+(?=[А-ЯЁA-Z«\"(]|[а-яё](?:\.\d)?\)\s)")

SECTION_TWO_TITLE = "Заключительные и переходные положения"


@dataclass(frozen=True)
class Chunk:
    id: str  # стабильный: "art-3-p-1", "art-5-p-1..2", "art-72-p-1-c2"
    embed_text: str  # что индексируем: заголовочный префикс + текст
    quote: str  # что показываем пользователю: только текст нормы
    ref: str  # "Статья 3, часть 1"
    chapter: int | None
    chapter_title: str | None
    article: str | None
    part: str | None  # первая часть чанка
    kind: str  # "article" | "preamble" | "transitional"


@dataclass
class _Group:
    """Одна или несколько подряд идущих единиц, которые станут одним чанком."""

    first: Unit
    parts: list[str | None]
    texts: list[str]

    @property
    def text(self) -> str:
        return " ".join(self.texts)


def _kind(u: Unit) -> str:
    if u.article:
        return "article"
    return "transitional" if u.section == "второй" else "preamble"


def _ref(u: Unit, parts: list[str | None]) -> str:
    known = [p for p in parts if p is not None]
    kind = _kind(u)
    if kind == "article":
        base = f"Статья {u.article}"
        if not known:
            return base
        if len(known) == 1:
            return f"{base}, часть {known[0]}"
        return f"{base}, части {known[0]}-{known[-1]}"
    if kind == "transitional":
        return f"Раздел второй, пункт {known[0]}" if known else "Раздел второй"
    return "Преамбула"


def _base_id(u: Unit, parts: list[str | None]) -> str:
    known = [p for p in parts if p is not None]
    if not known:
        suffix = ""
    elif len(known) == 1:
        suffix = f"-p-{known[0]}"
    else:
        suffix = f"-p-{known[0]}..{known[-1]}"
    kind = _kind(u)
    if kind == "article":
        return f"art-{u.article}{suffix}"
    if kind == "transitional":
        return f"trans{suffix}"
    return "preamble"


def _head(u: Unit) -> str:
    """Заголовочный префикс для embed_text. Пользователь его не видит."""
    if u.chapter and u.chapter_title:
        return f"Глава {u.chapter}. {u.chapter_title.capitalize()}. "
    if _kind(u) == "transitional":
        return f"{SECTION_TWO_TITLE}. "
    return ""


def _split_long(text: str, limit: int) -> list[str]:
    """Режет по границам предложений; соседние куски перекрываются одним предложением.
    Предложение длиннее limit остаётся целым: резать посреди нормы хуже, чем превысить лимит."""
    sentences = RE_SENTENCE.split(text)
    pieces: list[str] = []
    cur: list[str] = []
    for sent in sentences:
        if cur and len(" ".join([*cur, sent])) > limit:
            pieces.append(" ".join(cur))
            # перекрытие: последнее предложение куска повторяем в начале следующего,
            # но только если с ним новый кусок не превысит лимит сразу
            cur = [cur[-1], sent] if len(cur[-1]) + len(sent) + 1 <= limit else [sent]
        else:
            cur.append(sent)
    if cur:
        pieces.append(" ".join(cur))
    return pieces


def _group(units: list[Unit], min_chars: int) -> list[_Group]:
    """Короткую часть статьи сливаем со следующей частью ТОЙ ЖЕ статьи."""
    groups: list[_Group] = []
    for u in units:
        if groups:
            last = groups[-1]
            same_article = u.article is not None and last.first.article == u.article
            if same_article and len(last.text) < min_chars:
                last.parts.append(u.part)
                last.texts.append(u.text)
                continue
        groups.append(_Group(first=u, parts=[u.part], texts=[u.text]))
    return groups


def build_chunks(units: list[Unit], min_chars: int, max_chars: int, with_header: bool = True) -> list[Chunk]:
    """Превращает единицы парсера в чанки для индекса.

    Args:
        units: результат parse().
        min_chars: короче — сливаем со следующей частью той же статьи.
        max_chars: длиннее — режем по предложениям.
        with_header: добавлять ли в embed_text заголовок "Глава N. ... Статья M, часть K."
            (выключается только ради эксперимента на этапе 10).
    """
    chunks: list[Chunk] = []
    for g in _group(units, min_chars):
        u = g.first
        ref = _ref(u, g.parts)
        head = _head(u)
        base = _base_id(u, g.parts)
        text = g.text
        pieces = _split_long(text, max_chars) if len(text) > max_chars else [text]
        for idx, piece in enumerate(pieces, start=1):
            chunks.append(
                Chunk(
                    id=base if len(pieces) == 1 else f"{base}-c{idx}",
                    embed_text=f"{head}{ref}. {piece}" if with_header else piece,
                    quote=piece,
                    ref=ref,
                    chapter=u.chapter,
                    chapter_title=u.chapter_title,
                    article=u.article,
                    part=g.parts[0],
                    kind=_kind(u),
                )
            )
    return chunks
