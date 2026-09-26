import re

# "статья", "статьи", "статье", "статью", "статьёй", "статей" + сокращение "ст."
RE_ARTICLE_MENTION = re.compile(
    r"(?<![а-яё])(?:стать[а-яё]*|ст\.)\s*(\d{1,3}(?:\.\d)?)(?!\d)",
    re.IGNORECASE,
)
RE_ARTICLE_NUMBER = re.compile(r"\d{1,3}(?:\.\d)?")


def is_article_number(value: str) -> bool:
    """Похожа ли строка на номер статьи: "15", "67.1". Существование не проверяет."""
    return RE_ARTICLE_NUMBER.fullmatch(value) is not None


def extract_article_numbers(text: str) -> list[str]:
    """Номера статей, явно упомянутых в тексте, в порядке появления, без повторов.

    >>> extract_article_numbers("Что говорит статья 15? А ст. 67.1?")
    ['15', '67.1']
    """
    seen: list[str] = []
    for m in RE_ARTICLE_MENTION.finditer(text):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen
