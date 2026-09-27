from app.config import settings
from app.search.embedder import Embedder
from app.search.retriever import Retriever
from app.search.store import ChromaStore

QUERIES = [
    "кто является источником власти",
    "свобода вероисповедания",
    "презумпция невиновности",
    "неприкосновенность жилища",
    "сколько длится срок полномочий президента",
    "с какого возраста можно стать депутатом",
    "какой язык государственный",
    "можно ли судить дважды за одно преступление",
    "обязан ли я свидетельствовать против себя",
    "кто назначает председателя правительства",
]
NEGATIVE = ["какая погода в Москве", "как приготовить борщ"]


def top(retriever: Retriever, query: str, k: int = 3) -> str:
    """Короткая строка с top-k: статья, скор, источник."""
    hits = retriever.retrieve(query, k)
    return "  ".join(f"ст.{h.article or '-'}({h.score:.3f},{h.source})" for h in hits) or "—"


def main() -> None:
    """Печатает выдачу двух режимов бок о бок и скоры на негативных вопросах."""
    embedder = Embedder(settings.embedding_model, settings.embedding_device)
    store = ChromaStore(settings.chroma_path, settings.collection_name)
    no_threshold = {"min_score": 0.0}
    vector = Retriever(embedder, store, settings.model_copy(update=no_threshold | {"use_hybrid": False}))
    hybrid = Retriever(embedder, store, settings.model_copy(update=no_threshold))

    for q in QUERIES:
        print(f"\n{q}\n  vector: {top(vector, q)}\n  hybrid: {top(hybrid, q)}")

    print(f"\n--- негативные вопросы, порог min_score={settings.min_score}")
    real = Retriever(embedder, store, settings)
    for q in NEGATIVE:
        best = store.search(embedder.embed_query(q), 1)[0].score
        verdict = "отсечён" if not real.retrieve(q, 5) else "НЕ отсечён"
        print(f"  {q!r}: лучший скор {best:.3f} -> {verdict}")


if __name__ == "__main__":
    main()
