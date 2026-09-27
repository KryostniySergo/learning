from pydantic import BaseModel, Field

from app.search.store import Hit

DISCLAIMER = "Ответ содержит выдержки из текста Конституции РФ и не является юридической консультацией."


class Citation(BaseModel):
    """Одна цитата: точный текст фрагмента и ссылка на его место в Конституции."""

    ref: str
    article: str | None = None
    part: str | None = None
    quote: str
    score: float | None = None  # None, если фрагмент выбран точно, а не поиском
    match: str  # как найден: vector | lexical | both | exact

    @classmethod
    def from_hit(cls, hit: Hit) -> "Citation":
        """Переводит внутренний Hit хранилища во внешний формат API.

        У точной выборки (match="exact") скора нет: смысл там не сравнивался.
        """
        return cls(
            ref=hit.ref,
            article=hit.article,
            part=hit.part,
            quote=hit.quote,
            score=None if hit.source == "exact" else round(hit.score, 4),
            match=hit.source,
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


class AskRequest(BaseModel):
    """Тело POST /ask."""

    question: str = Field(min_length=3, max_length=500, description="Вопрос на естественном языке")
    k: int = Field(default=5, ge=1, le=10, description="Сколько фрагментов дать модели")


class AskResponse(BaseModel):
    """Ответ /ask.

    found     — нашлись ли в Конституции фрагменты по вопросу;
    answer    — связный ответ модели или null (LLM выключена, упала, не нашла ответа);
    message   — пояснение для человека, почему ответа нет;
    citations — фрагменты из БД; их текст всегда совпадает с хранилищем, модель его не меняет.
    """

    found: bool
    answer: str | None = None
    message: str | None = None
    citations: list[Citation]
    llm_used: bool
    took_ms: int
    disclaimer: str = DISCLAIMER
