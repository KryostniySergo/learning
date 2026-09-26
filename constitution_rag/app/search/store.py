from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb

from app.ingest.chunker import Chunk

DISTANCE_SPACE = "cosine"


@dataclass(frozen=True)
class Hit:
    """Один найденный фрагмент в том виде, в каком его отдаёт хранилище."""

    id: str
    quote: str
    ref: str
    article: str | None
    part: str | None
    score: float  # косинусная близость: 1.0 — совпадение, чем больше, тем релевантнее


def _clean_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    """Убирает None: Chroma принимает в метаданных только str/int/float/bool."""
    return {k: v for k, v in meta.items() if v is not None}


def _to_hit(cid: str, doc: str, meta: dict[str, Any], score: float) -> Hit:
    """Собирает Hit из одной записи Chroma."""
    return Hit(
        id=cid,
        quote=doc,
        ref=meta.get("ref", ""),
        article=meta.get("article"),
        part=meta.get("part"),
        score=score,
    )


class ChromaStore:
    """Работа с одной коллекцией Chroma, лежащей на диске."""

    def __init__(self, path: Path, collection_name: str) -> None:
        """Открывает (или создаёт) коллекцию.

        Args:
            path: папка, где Chroma хранит sqlite и индекс.
            collection_name: имя коллекции; содержит версию модели эмбеддингов.
        """
        self._client = chromadb.PersistentClient(path=str(path))
        self._name = collection_name
        self._collection = self._open()

    def _open(self):
        """Открывает коллекцию, создавая её с косинусной метрикой при первом обращении.

        Метрика задаётся ТОЛЬКО при создании и потом не меняется. Если коллекцию
        однажды создали без неё, она навсегда останется на L2 — лечится только --recreate.
        """
        return self._client.get_or_create_collection(
            name=self._name,
            configuration={"hnsw": {"space": DISTANCE_SPACE}},
        )

    @property
    def distance_space(self) -> str:
        """Метрика, с которой реально создана коллекция ("cosine", "l2" или "ip")."""
        hnsw = self._collection.configuration.get("hnsw") or {}
        return hnsw.get("space", "unknown")

    def recreate(self) -> None:
        """Удаляет коллекцию целиком и создаёт пустую заново."""
        try:
            self._client.delete_collection(self._name)
        except Exception:  # коллекции могло не быть — это не ошибка  # noqa: S110
            pass
        self._collection = self._open()

    def count(self) -> int:
        """Сколько записей в коллекции."""
        return self._collection.count()

    def ids(self) -> set[str]:
        """Все id в коллекции (без текстов и векторов)."""
        return set(self._collection.get(include=[])["ids"])

    def delete(self, ids: list[str]) -> None:
        """Удаляет записи по id."""
        if ids:
            self._collection.delete(ids=ids)

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]], batch: int = 512) -> None:
        """Записывает чанки с векторами. Существующие id перезаписываются, дубликатов нет.

        В метаданные кладём seq — порядковый номер чанка в документе. По нему потом
        восстанавливается исходный порядок частей статьи.
        """
        if len(chunks) != len(vectors):
            raise ValueError(f"чанков {len(chunks)}, а векторов {len(vectors)}")
        for start in range(0, len(chunks), batch):
            part = chunks[start : start + batch]
            self._collection.upsert(
                ids=[c.id for c in part],
                embeddings=vectors[start : start + batch],
                documents=[c.quote for c in part],
                metadatas=[
                    _clean_metadata(
                        {
                            "seq": start + i,
                            "ref": c.ref,
                            "article": c.article,
                            "part": c.part,
                            "chapter": c.chapter,
                            "chapter_title": c.chapter_title,
                            "kind": c.kind,
                        }
                    )
                    for i, c in enumerate(part)
                ],
            )

    def search(self, vector: list[float], k: int, where: dict | None = None) -> list[Hit]:
        """Возвращает k ближайших к вектору чанков, лучшие первыми.

        Chroma возвращает косинусное РАССТОЯНИЕ: distance = 1 - cos_similarity,
        от 0 (совпадение) до 2 (противоположность). Переводим обратно в близость:
        score = 1 - distance. Все пороги (min_score) задаются в терминах близости.
        """
        n = min(k, self.count())
        if n == 0:
            return []
        res = self._collection.query(
            query_embeddings=[vector],
            n_results=n,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        return [
            _to_hit(cid, doc, meta, score=1.0 - float(dist))
            for cid, doc, meta, dist in zip(
                res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0], strict=False
            )
        ]

    def _get(self, **kwargs) -> list[tuple[int, Hit]]:
        """Точная выборка без вектора. Возвращает пары (seq, Hit) со скором 0."""
        res = self._collection.get(include=["documents", "metadatas"], **kwargs)
        return [
            (meta.get("seq", 0), _to_hit(cid, doc, meta, score=0.0))
            for cid, doc, meta in zip(res["ids"], res["documents"], res["metadatas"], strict=False)
        ]

    def get_by_ids(self, ids: list[str]) -> dict[str, Hit]:
        """Чанки по списку id (порядок не гарантирован, поэтому словарь)."""
        if not ids:
            return {}
        return {hit.id: hit for _, hit in self._get(ids=ids)}

    def get_by_article(self, article: str) -> list[Hit]:
        """Все чанки статьи в порядке следования в тексте. Пустой список, если статьи нет."""
        rows = self._get(where={"article": article})
        return [hit for _, hit in sorted(rows, key=lambda r: r[0])]

    def all_chunks(self) -> list[Hit]:
        """Все чанки коллекции в порядке документа (нужно для BM25)."""
        return [hit for _, hit in sorted(self._get(), key=lambda r: r[0])]
