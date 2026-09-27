import argparse
import csv
import statistics
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.search.embedder import Embedder
from app.search.retriever import Retriever
from app.search.store import ChromaStore

K_VALUES = (1, 3, 5)
MAX_K = max(K_VALUES)


@dataclass(frozen=True)
class Case:
    """Один вопрос эталонного набора."""

    question: str
    expected: frozenset[str]  # пустое множество — негативный вопрос

    @property
    def is_negative(self) -> bool:
        """Вопрос, на который ответа в Конституции нет."""
        return not self.expected


@dataclass(frozen=True)
class Outcome:
    """Что ретривер сделал с вопросом — без учёта порога, чтобы порог можно было перебирать."""

    case: Case
    articles: list[str | None]  # статьи top-MAX_K в порядке выдачи
    best_score: float | None  # лучшая векторная близость; None для точной выборки
    exact: bool  # сработала точная выборка по номеру статьи

    def refused(self, threshold: float) -> bool:
        """Отсёк бы ретривер этот вопрос при данном пороге (так же, как Retriever.retrieve)."""
        return not self.exact and (self.best_score is None or self.best_score < threshold)

    def rank(self) -> int | None:
        """Место первой ожидаемой статьи в выдаче (с 1) или None."""
        for i, article in enumerate(self.articles, start=1):
            if article in self.case.expected:
                return i
        return None


def load_cases(path: Path) -> list[Case]:
    """Читает CSV с вопросами."""
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [
        Case(
            question=row["question"].strip(),
            expected=frozenset()
            if row["expected_article"].strip() == "NONE"
            else frozenset(a.strip() for a in row["expected_article"].split("|")),
        )
        for row in rows
    ]


def run(cases: list[Case], retriever: Retriever, embedder: Embedder, store: ChromaStore) -> list[Outcome]:
    """Прогоняет вопросы через ретривер с выключенным порогом и запоминает лучший скор."""
    outcomes = []
    for case in cases:
        hits = retriever.retrieve(case.question, MAX_K)
        exact = bool(hits) and hits[0].source == "exact"
        best = None
        if not exact:
            top = store.search(embedder.embed_query(case.question), 1)
            best = top[0].score if top else None
        outcomes.append(Outcome(case, [h.article for h in hits], best, exact))
    return outcomes


@dataclass(frozen=True)
class Metrics:
    """Метрики при конкретном пороге."""

    recall: dict[int, float]
    mrr: float
    false_refusal: float
    refusal_acc: float


def compute(outcomes: list[Outcome], threshold: float) -> Metrics:
    """recall@k и MRR по позитивным вопросам, отказы — по обоим типам.

    Позитивный вопрос, отсечённый порогом, считается промахом во всех метриках:
    пользователь ответа не увидит.
    """
    pos = [o for o in outcomes if not o.case.is_negative]
    neg = [o for o in outcomes if o.case.is_negative]
    hits_at = {k: 0 for k in K_VALUES}
    rr = 0.0
    refused_pos = 0
    for o in pos:
        if o.refused(threshold):
            refused_pos += 1
            continue
        rank = o.rank()
        if rank is None:
            continue
        rr += 1 / rank
        for k in K_VALUES:
            hits_at[k] += rank <= k
    n = len(pos) or 1
    return Metrics(
        recall={k: v / n for k, v in hits_at.items()},
        mrr=rr / n,
        false_refusal=refused_pos / n,
        refusal_acc=(sum(o.refused(threshold) for o in neg) / len(neg)) if neg else float("nan"),
    )


def describe(scores: list[float]) -> str:
    """min / median / max списка скоров."""
    if not scores:
        return "—"
    return f"min={min(scores):.3f} med={statistics.median(scores):.3f} max={max(scores):.3f}"


def suggest_threshold(outcomes: list[Outcome]) -> tuple[float, str]:
    """Порог по распределению скоров.

    Если все негативные ниже всех позитивных — берём середину зазора (запас в обе стороны).
    Иначе — перебираем пороги и берём лучший компромисс refusal_acc + (1 - false_refusal).
    """
    pos = [o.best_score for o in outcomes if not o.case.is_negative and o.best_score is not None]
    neg = [o.best_score for o in outcomes if o.case.is_negative and o.best_score is not None]
    if not pos or not neg:
        return settings.min_score, "недостаточно данных"
    if max(neg) < min(pos):
        return round((max(neg) + min(pos)) / 2, 3), "классы разделимы, середина зазора"
    candidates = sorted({round(s + d, 3) for s in pos + neg for d in (0.0, 0.001)})
    best = max(
        candidates, key=lambda t: (compute(outcomes, t).refusal_acc + 1 - compute(outcomes, t).false_refusal, -t)
    )
    return best, "классы пересекаются, лучший компромисс"


def main() -> None:
    """Печатает метрики, распределение скоров, подсказку по порогу и разбор ошибок."""
    ap = argparse.ArgumentParser(description="Метрики качества поиска")
    ap.add_argument("--csv", type=Path, default=Path("eval/questions.csv"))
    ap.add_argument("--tag", help="название эксперимента: напечатать строку для таблицы README")
    args = ap.parse_args()

    cases = load_cases(args.csv)
    embedder = Embedder.from_settings(settings)
    store = ChromaStore(settings.chroma_path, settings.collection_name)
    if store.count() == 0:
        raise SystemExit(f"коллекция {settings.collection_name} пуста — сначала ingest")
    retriever = Retriever(embedder, store, settings.model_copy(update={"min_score": 0.0}))
    outcomes = run(cases, retriever, embedder, store)

    n_pos = sum(not c.is_negative for c in cases)
    print(f"коллекция: {settings.collection_name} ({store.count()} чанков), модель: {settings.embedding_model}")
    print(
        f"hybrid={settings.use_hybrid} stemming={settings.bm25_stemming} "
        f"header={settings.chunk_header} e5_prefixes={settings.e5_prefixes}"
    )
    print(f"вопросов: {len(cases)} (позитивных {n_pos}, негативных {len(cases) - n_pos})\n")

    for title, thr in (("без порога", 0.0), (f"с порогом {settings.min_score}", settings.min_score)):
        m = compute(outcomes, thr)
        recall = "  ".join(f"recall@{k}={v:.1%}" for k, v in m.recall.items())
        print(
            f"{title:18} {recall}  MRR={m.mrr:.3f}  "
            f"refusal acc={m.refusal_acc:.0%}  false refusal={m.false_refusal:.0%}"
        )

    pos_scores = [o.best_score for o in outcomes if not o.case.is_negative and o.best_score is not None]
    neg_scores = [o.best_score for o in outcomes if o.case.is_negative and o.best_score is not None]
    print(f"\nскоры позитивных: {describe(pos_scores)}")
    print(f"скоры негативных: {describe(neg_scores)}")
    thr, why = suggest_threshold(outcomes)
    m = compute(outcomes, thr)
    print(
        f"→ предлагаемый min_score={thr} ({why}): refusal acc={m.refusal_acc:.0%}, "
        f"false refusal={m.false_refusal:.0%}, recall@5={m.recall[5]:.1%}"
    )

    print("\nгде ожидаемой статьи нет в top-5 (без порога):")
    misses = [o for o in outcomes if not o.case.is_negative and o.rank() is None]
    for o in misses:
        got = ", ".join(a or "—" for a in o.articles[:3])
        print(f"  {o.case.question}  ждали {'|'.join(sorted(o.case.expected))}, получили {got}")
    if not misses:
        print("  нет")

    print("\nнегативные вопросы, отсортированы по опасности (лучший скор сверху):")
    for o in sorted((o for o in outcomes if o.case.is_negative), key=lambda o: -(o.best_score or 0)):
        print(f"  {o.best_score:.3f}  {o.case.question}")

    if args.tag:
        m = compute(outcomes, settings.min_score)
        print("\nстрока для README:")
        print(
            f"| {args.tag} | {m.recall[1]:.1%} | {m.recall[3]:.1%} | {m.recall[5]:.1%} | "
            f"{m.mrr:.3f} | {m.refusal_acc:.0%} | {m.false_refusal:.0%} |"
        )


if __name__ == "__main__":
    main()
