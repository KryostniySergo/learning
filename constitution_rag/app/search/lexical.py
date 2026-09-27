import re

import snowballstemmer
from rank_bm25 import BM25Okapi

# слово или число; "67.1" остаётся одним токеном
RE_TOKEN = re.compile(r"[а-яa-z]+|\d+(?:\.\d+)?")
_STEMMER = snowballstemmer.stemmer("russian")


def tokenize(text: str, stem: bool = True) -> list[str]:
    """Режет текст на токены: нижний регистр, ё -> е, по желанию — стемминг.

    Стемминг обрезает окончания: "президента", "президентом" -> "президент".
    Без него BM25 считает разные формы одного слова разными словами.
    """
    tokens = RE_TOKEN.findall(text.lower().replace("ё", "е"))
    return _STEMMER.stemWords(tokens) if stem else tokens


class BM25Index:
    """Индекс BM25 в памяти по фиксированному набору фрагментов."""

    def __init__(self, ids: list[str], texts: list[str], stem: bool = True) -> None:
        """Строит индекс.

        Args:
            ids: id фрагментов, в том же порядке, что и texts.
            texts: тексты для индексации.
            stem: применять ли стемминг (и к документам, и к запросам — одинаково).
        """
        if len(ids) != len(texts):
            raise ValueError("ids и texts разной длины")
        self.ids = ids
        self._stem = stem
        self._bm25 = BM25Okapi([tokenize(t, stem) for t in texts])

    def search(self, query: str, k: int) -> list[str]:
        """До k id с наибольшим BM25-скором. Фрагменты без единого общего слова не попадают."""
        scores = self._bm25.get_scores(tokenize(query, self._stem))
        ranked = sorted(zip(scores, self.ids), key=lambda pair: -pair[0])
        return [doc_id for score, doc_id in ranked[:k] if score > 0]
