import re

# Разметка ролей чата: "system:", "assistant:", "user:" в начале строки или после пробела
RE_ROLE_MARKUP = re.compile(r"(?i)\b(system|assistant|user|developer)\s*:")
# Служебные теги, которыми мы сами размечаем промпт, — пользователь не должен их подделать
RE_PROMPT_TAGS = re.compile(r"</?\s*(документы|вопрос)\s*>", re.IGNORECASE)
# Управляющие символы, кроме обычных пробельных
RE_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Типовые формулировки попыток перехватить управление моделью
RE_INJECTION = re.compile(
    r"(игнорир\w*|забудь\w*|отмени\w*).{0,40}(инструкц|правил|предыдущ|указани)"
    r"|ignore\s+(all|any|previous|the)\b|disregard\s+(all|previous)",
    re.IGNORECASE,
)


def sanitize_question(text: str, max_len: int = 500) -> str:
    """Чистит вопрос: убирает управляющие символы, разметку ролей и наши теги, режет длину.

    Это не защита от prompt injection как таковой (её гарантирует только устройство
    промпта и проверка ответа), а снижение поверхности атаки и мусора в логах.
    """
    text = RE_CONTROL.sub(" ", text)
    text = RE_PROMPT_TAGS.sub(" ", text)
    text = RE_ROLE_MARKUP.sub(" ", text)
    text = " ".join(text.split())
    return text[:max_len]


def looks_like_injection(text: str) -> bool:
    """Похож ли вопрос на попытку управлять моделью. Только для логов и мониторинга."""
    return RE_INJECTION.search(text) is not None
