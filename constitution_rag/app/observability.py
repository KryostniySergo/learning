import json
import logging
import time
from contextvars import ContextVar
from typing import Any

# Идентификатор текущего запроса. ContextVar — "глобальная" переменная, у которой
# своё значение в каждом запросе: параллельные запросы не видят чужой request_id.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Добавляет в каждую запись лога поле request_id из текущего контекста."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Дописывает request_id и пропускает запись дальше."""
        record.request_id = request_id_var.get()
        return True


def setup_logging(level: str = "INFO") -> None:
    """Настраивает корневой логгер: единый формат с request_id для всего приложения."""
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]  # без дублей при повторном вызове (например, --reload)
    root.setLevel(level)


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Пишет событие одной JSON-строкой: её легко искать grep'ом и разбирать скриптом."""
    payload = {"event": event, "request_id": request_id_var.get(), **fields}
    logger.info(json.dumps(payload, ensure_ascii=False, default=str))


class Stopwatch:
    """Секундомер для замера этапов: with Stopwatch() as sw: ...; sw.ms."""

    def __enter__(self) -> "Stopwatch":
        """Запускает отсчёт."""
        self._start = time.perf_counter()
        self.ms = 0
        return self

    def __exit__(self, *exc) -> None:
        """Фиксирует длительность в миллисекундах (даже если внутри было исключение)."""
        self.ms = int((time.perf_counter() - self._start) * 1000)
