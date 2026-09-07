import json
import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.models.idempotency_key import IdempotencyKey
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)

HEADER_NAME = "Idempotency-Key"
PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Возвращает сохранённый ответ при повторе запроса с тем же ключом.

    Заголовок Idempotency-Key необязателен: без него запрос обрабатывается
    обычным образом. С ним результат первой успешной обработки сохраняется
    и отдаётся на все последующие запросы с этим же ключом.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Обрабатывает запрос с учётом ключа идемпотентности.

        Args:
            request (Request): входящий запрос.
            call_next (RequestResponseEndpoint): следующий обработчик в цепочке.

        Returns:
            Response: сохранённый либо свежий ответ.
        """
        key = request.headers.get(HEADER_NAME)
        if key is None or request.method not in PROTECTED_METHODS:
            return await call_next(request)

        async with UnitOfWork() as uow:
            saved = await uow.idempotency.get_active(key)

        if saved is not None:
            logger.info("idempotent replay for key %s", key)
            return JSONResponse(
                status_code=saved.status_code,
                content=json.loads(saved.response_body),
                headers={"Idempotency-Replayed": "true"},
            )

        response = await call_next(request)

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        if 200 <= response.status_code < 300:
            await self._save(key, request, response.status_code, body)

        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

    async def _save(self, key: str, request: Request, status_code: int, body: bytes) -> None:
        """Сохраняет результат успешной операции.

        Гонка двух одновременных запросов с одним ключом отсекается уникальным
        индексом: проигравший просто не сохранит свою запись.

        Args:
            key (str): значение заголовка Idempotency-Key.
            request (Request): исходный запрос.
            status_code (int): код ответа.
            body (bytes): тело ответа.
        """
        try:
            async with UnitOfWork() as uow:
                uow.idempotency.add(
                    IdempotencyKey(
                        key=key,
                        method=request.method,
                        path=request.url.path,
                        status_code=status_code,
                        response_body=body.decode("utf-8"),
                    )
                )
                await uow.commit()
        except Exception:
            logger.warning("failed to store idempotency key %s", key, exc_info=True)
