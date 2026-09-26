from pydantic import BaseModel

from app.search.store import Hit

DISCLAIMER = "Ответ содержит выдержки из текста Конституции РФ и не является юридической консультацией."


class Citation(BaseModel):
    """Одна цитата: точный текст фрагмента и ссылка на его место в Конституции."""

    ref: str
    article: str | None = None
    part: str | None = None
    quote: str
    score: float | None = None  # None, если фрагмент выбран точно, а не поиском

    @classmethod
    def from_hit(cls, hit: Hit, with_score: bool = True) -> "Citation":
        """Переводит внутренний Hit хранилища во внешний формат API.

        Args:
            hit: фрагмент из хранилища.
            with_score: False для точной выборки по номеру — там скор не имеет смысла.
        """
        return cls(
            ref=hit.ref,
            article=hit.article,
            part=hit.part,
            quote=hit.quote,
            score=round(hit.score, 4) if with_score else None,
        )


class SearchResponse(BaseModel):
    """Ответ /search: найденные цитаты и служебная информация."""

    query: str
    took_ms: int
    collection: str
    results: list[Citation]
    disclaimer: str = DISCLAIMER


class ArticleResponse(BaseModel):
    """Ответ /articles/{number}: все фрагменты статьи в порядке текста."""

    article: str
    parts: list[Citation]
    disclaimer: str = DISCLAIMER
