# tests/test_article_ref.py
import pytest
from app.search.article_ref import extract_article_numbers, is_article_number


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("статья 15", ["15"]),
        ("Что говорит статья 15?", ["15"]),
        ("покажи статью 31", ["31"]),
        ("в статье 67.1 сказано", ["67.1"]),
        ("ст. 49 и ст.50", ["49", "50"]),
        ("СТАТЬЯ 3", ["3"]),
        ("статья 3 и снова статья 3", ["3"]),
        ("статьи 20, 21", ["20"]),  # перечисление после первого номера не ловим
        ("кто источник власти", []),
        ("статус президента 2024 года", []),  # "статус" — не "статья"
        ("часть 3 статьи", []),  # номер относится к части, не к статье
    ],
)
def test_extract_article_numbers(text, expected):
    """Номера статей находятся в разных падежах и в сокращении "ст."."""
    assert extract_article_numbers(text) == expected


@pytest.mark.parametrize(("value", "ok"), [("3", True), ("67.1", True), ("abc", False), ("3.", False), ("1234", False)])
def test_is_article_number(value, ok):
    """Формат номера статьи: 1–3 цифры и необязательный .N."""
    assert is_article_number(value) is ok
