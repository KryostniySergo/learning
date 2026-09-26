from app.config import settings
from app.search.embedder import Embedder


def cos(a: list[float], b: list[float]) -> float:
    """Косинусная близость нормализованных векторов — просто скалярное произведение."""
    return sum(x * y for x, y in zip(a, b))


emb = Embedder(settings.embedding_model, settings.embedding_device)
print(f"модель: {emb.model_name}, dim={emb.dim}")

docs = {
    "ст.3 (власть)": "Носителем суверенитета и единственным источником власти в Российской "
    "Федерации является ее многонациональный народ.",
    "ст.118 (суды)": "Правосудие в Российской Федерации осуществляется только судом.",
    "ст.28 (религия)": "Каждому гарантируется свобода совести, свобода вероисповедания.",
}
doc_vecs = dict(zip(docs, emb.embed_documents(list(docs.values()))))

for query in ["кто источник власти", "кто вершит правосудие", "можно ли верить в бога", "как приготовить борщ"]:
    q = emb.embed_query(query)
    scores = "  ".join(f"{name}={cos(q, v):.3f}" for name, v in doc_vecs.items())
    print(f"{query!r:28} {scores}")
