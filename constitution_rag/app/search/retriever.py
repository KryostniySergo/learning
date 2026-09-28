# app/search/retriever.py
"""Логика поиска: точная выборка по номеру статьи, вектор + BM25 через RRF, порог "не найдено"."""

import logging
import threading
from dataclasses import replace

from app.observability import Stopwatch
from app.search.article_ref import extract_article_numbers
from app.search.embedder import Embedder
from app.search.lexical import BM25Index
from app.search.store import ChromaStore, Hit

logger = logging.getLogger(__name__)


def rrf(rankings: list[list[str]], k: int = 60) -> list[str]:
    """Reciprocal Rank Fusion: объединяет несколько ранжированных списков в один.

    Каждый документ получает сумму 1 / (k + место) по всем спискам, где он есть.
    Складываются места, а не скоры: косинус и BM25 измеряются в несравнимых шкалах.
    k сглаживает разницу между первыми местами (60 — значение из оригинальной статьи).
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda doc_id: -scores[doc_id])


class Retriever:
    """Единая точка поиска для API и скриптов оценки: вопрос -> список найденных фрагментов."""

    def __init__(self, embedder: Embedder, store: ChromaStore, settings) -> None:
        """Запоминает зависимости и пытается сразу построить BM25-индекс.

        Args:
            embedder: модель для кодирования запроса.
            store: векторное хранилище.
            settings: candidate_k, min_score, use_hybrid, bm25_stemming, rrf_k.
        """
        self._embedder = embedder
        self._store = store
        self._settings = settings
        self._bm25: BM25Index | None = None
        self._lock = threading.Lock()
        self.refresh()

    def refresh(self) -> None:
        """(Пере)строит BM25-индекс по текущему содержимому хранилища.

        Текст для BM25 — ссылка + цитата: так номер статьи из ref тоже ищется по словам.
        Если хранилище пустое, индекс остаётся None и будет построен при первом запросе.
        """
        if not self._settings.use_hybrid:
            return
        chunks = self._store.all_chunks()
        index = (
            BM25Index(
                [c.id for c in chunks], [f"{c.ref}. {c.quote}" for c in chunks], stem=self._settings.bm25_stemming
            )
            if chunks
            else None
        )
        with self._lock:
            self._bm25 = index
        logger.info("bm25 index: %d chunks", len(chunks))

    def retrieve(self, query: str, k: int, trace: dict | None = None) -> list[Hit]:
        """До k фрагментов по вопросу, лучшие первыми. Пустой список означает "не найдено".

        Порядок работы:
        1. Если в вопросе прямо названа статья — точная выборка её частей, без вектора.
        2. Векторный поиск candidate_k кандидатов.
        3. Порог: если даже лучший кандидат ниже min_score — ответа нет.
        4. Гибрид (если включён): BM25 и слияние двух списков через RRF.

        Args:
            trace: необязательный словарь, куда записываются подробности для логов:
                route (exact | empty | refused | vector | hybrid), best_score,
                embed_ms, search_ms, bm25_ms.
        """
        trace = {} if trace is None else trace

        with Stopwatch() as sw:
            exact = self._exact(query, k)
        if exact:
            trace.update(route="exact", search_ms=sw.ms)
            return exact

        with Stopwatch() as sw:
            vector = self._embedder.embed_query(query)
        trace["embed_ms"] = sw.ms

        with Stopwatch() as sw:
            candidates = self._store.search(vector, self._settings.candidate_k)
        trace["search_ms"] = sw.ms
        if not candidates:
            trace["route"] = "empty"
            return []

        best = max(h.score for h in candidates)
        trace["best_score"] = round(best, 4)
        if best < self._settings.min_score:
            trace["route"] = "refused"
            return []

        bm25 = self._get_bm25()
        if bm25 is None:
            trace["route"] = "vector"
            return candidates[:k]

        with Stopwatch() as sw:
            result = self._fuse(query, vector, candidates, bm25, k)
        trace.update(route="hybrid", bm25_ms=sw.ms)
        return result

    def _fuse(self, query: str, vector: list[float], candidates: list[Hit], bm25: BM25Index, k: int) -> list[Hit]:
        """BM25 по вопросу + слияние с векторными кандидатами через RRF."""
        lexical_ids = bm25.search(query, self._settings.candidate_k)
        vector_ids = [h.id for h in candidates]

        # у чанков, найденных только BM25, нет векторного скора — досчитываем его,
        # иначе они выпали бы из выдачи или показались бы со скором 0
        by_id = {h.id: h for h in candidates}
        missing = [i for i in lexical_ids if i not in by_id]
        by_id.update(self._store.get_by_ids(missing, vector))

        in_vector, in_lexical = set(vector_ids), set(lexical_ids)
        fused = rrf([vector_ids, lexical_ids], k=self._settings.rrf_k)

        result: list[Hit] = []
        for doc_id in fused:
            if doc_id not in by_id:
                continue
            source = (
                "both"
                if doc_id in in_vector and doc_id in in_lexical
                else "vector"
                if doc_id in in_vector
                else "lexical"
            )
            result.append(replace(by_id[doc_id], source=source))
            if len(result) == k:
                break
        return result

    def _exact(self, query: str, k: int) -> list[Hit]:
        """Части статей, прямо названных в вопросе ("статья 15"). Пусто, если таких нет."""
        hits: list[Hit] = []
        for number in extract_article_numbers(query):
            hits.extend(self._store.get_by_article(number))
        return hits[:k]

    def _get_bm25(self) -> BM25Index | None:
        """BM25-индекс; строится лениво, если при старте хранилище было пустым."""
        if not self._settings.use_hybrid:
            return None
        if self._bm25 is None and self._store.count() > 0:
            self.refresh()
        return self._bm25
