import argparse
import time

from app.config import settings
from app.ingest.chunker import build_chunks
from app.ingest.loader import load_text
from app.ingest.parser import parse
from app.search.embedder import Embedder
from app.search.store import DISTANCE_SPACE, ChromaStore


def run(store: ChromaStore, embedder: Embedder, recreate: bool = False) -> None:
    """Собирает чанки из исходника и синхронизирует с ними коллекцию.

    После запуска в коллекции лежат ровно текущие чанки: новые добавлены,
    изменённые перезаписаны, устаревшие (чьих id больше нет) удалены.
    """
    started = time.perf_counter()

    units = parse(load_text(settings.source_path))
    chunks = build_chunks(units, settings.min_chunk_chars, settings.max_chunk_chars)
    ids = [c.id for c in chunks]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise SystemExit(f"неуникальные id чанков: {dupes}")
    print(f"единиц: {len(units)}, чанков: {len(chunks)}")

    if recreate:
        store.recreate()
        print("коллекция пересоздана")
    if store.distance_space != DISTANCE_SPACE:
        raise SystemExit(
            f"коллекция создана с метрикой {store.distance_space!r}, нужна {DISTANCE_SPACE!r}. Запусти с --recreate."
        )
    before = store.count()

    t0 = time.perf_counter()
    vectors = embedder.embed_documents([c.embed_text for c in chunks])
    embed_s = time.perf_counter() - t0

    store.upsert(chunks, vectors)
    stale = sorted(store.ids() - set(ids))
    store.delete(stale)

    print(f"эмбеддинги: {embed_s:.1f} с, dim={embedder.dim}")
    print(f"в коллекции было {before}, стало {store.count()}, удалено устаревших: {len(stale)}")
    print(f"коллекция: {settings.collection_name}, метрика: {store.distance_space}")
    print(f"всего: {time.perf_counter() - started:.1f} с")


def main() -> None:
    """Точка входа CLI."""
    ap = argparse.ArgumentParser(description="Построить индекс Конституции в Chroma")
    ap.add_argument("--recreate", action="store_true", help="удалить коллекцию и собрать заново")
    args = ap.parse_args()

    store = ChromaStore(settings.chroma_path, settings.collection_name)
    embedder = Embedder(settings.embedding_model, settings.embedding_device)
    run(store, embedder, recreate=args.recreate)


if __name__ == "__main__":
    main()
