import logging
import time
import uuid
from collections import deque

from fastapi import Request
from fastapi.responses import JSONResponse

from app.observability import log_event, request_id_var

logger = logging.getLogger("app.access")

RATE_LIMIT_EXEMPT = {"/healthz", "/readyz"}  # пробы оркестратора не должны упираться в лимит


class RateLimiter:
    """Скользящее окно в памяти: не больше limit запросов за window секунд с одного ключа.

    Подходит для одного процесса. При нескольких воркерах или репликах у каждого
    свой счётчик, и нужен общий (например, Redis).
    """

    def __init__(self, limit: int, window: float = 60.0, max_keys: int = 10_000) -> None:
        """limit <= 0 отключает ограничение; max_keys — после скольких клиентов чистить память."""
        self.limit = limit
        self.window = window
        self.max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}

    def check(self, key: str, now: float | None = None) -> float:
        """Регистрирует запрос. Возвращает 0, если он разрешён, иначе — сколько секунд ждать."""
        if self.limit <= 0:
            return 0.0
        now = time.monotonic() if now is None else now
        if len(self._hits) > self.max_keys:
            self.cleanup(now)
        bucket = self._hits.setdefault(key, deque())
        while bucket and now - bucket[0] >= self.window:
            bucket.popleft()  # выкидываем запросы старше окна
        if len(bucket) >= self.limit:
            return self.window - (now - bucket[0])
        bucket.append(now)
        return 0.0

    def cleanup(self, now: float | None = None) -> None:
        """Удаляет ключи без свежих запросов, чтобы словарь не рос бесконечно."""
        now = time.monotonic() if now is None else now
        stale = [k for k, b in self._hits.items() if not b or now - b[-1] >= self.window]
        for k in stale:
            del self._hits[k]


async def rate_limit_middleware(request: Request, call_next):
    """Отвечает 429, если клиент превысил лимит запросов в минуту."""
    limiter: RateLimiter = request.app.state.rate_limiter
    if request.url.path not in RATE_LIMIT_EXEMPT:
        client = request.client.host if request.client else "unknown"
        wait = limiter.check(client)
        if wait > 0:
            return JSONResponse(
                {"detail": "Слишком много запросов, попробуйте позже"},
                status_code=429,
                headers={"Retry-After": str(int(wait) + 1)},
            )
    return await call_next(request)


async def request_context_middleware(request: Request, call_next):
    """Назначает запросу request_id, пишет access-лог и возвращает id в заголовке ответа.

    request_id берётся из заголовка X-Request-ID (если его прислал клиент или прокси)
    или генерируется. Он кладётся в ContextVar — и попадает во все логи этого запроса.
    """
    incoming = request.headers.get("X-Request-ID", "")
    request_id = incoming[:64] if incoming.isprintable() and incoming else uuid.uuid4().hex[:12]
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        log_event(
            logger,
            "http",
            method=request.method,
            path=request.url.path,
            status=status,
            took_ms=int((time.perf_counter() - started) * 1000),
        )
        request_id_var.reset(token)
