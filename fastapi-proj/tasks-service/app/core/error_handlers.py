import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    CrossCompanyAccessError,
    InvalidStatusTransitionError,
    NotAuthenticatedError,
    NotAuthorizedError,
    TaskNotFoundError,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)


def _error_response(status_code: int, detail: str) -> JSONResponse:
    """Собирает единообразный JSON-ответ об ошибке.

    Args:
        status_code (int): HTTP-код ответа.
        detail (str): текст ошибки для клиента.

    Returns:
        JSONResponse: готовый ответ.
    """
    return JSONResponse(status_code=status_code, content={"detail": detail})


def register_exception_handlers(app: FastAPI) -> None:
    """Регистрирует обработчики доменных исключений на уровне приложения.

    Args:
        app (FastAPI): экземпляр приложения.
    """

    @app.exception_handler(NotAuthenticatedError)
    async def handle_not_authenticated(
        request: Request, exc: NotAuthenticatedError
    ) -> JSONResponse:
        """Отдаёт 401, если запрос без валидного токена."""
        return _error_response(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    @app.exception_handler(NotAuthorizedError)
    async def handle_not_authorized(request: Request, exc: NotAuthorizedError) -> JSONResponse:
        """Отдаёт 403, если у пользователя нет прав на изменение задачи."""
        return _error_response(
            status.HTTP_403_FORBIDDEN, "Only author, responsible or admin can modify this task"
        )

    @app.exception_handler(TaskNotFoundError)
    async def handle_task_not_found(request: Request, exc: TaskNotFoundError) -> JSONResponse:
        """Отдаёт 404, если задача не найдена."""
        return _error_response(status.HTTP_404_NOT_FOUND, "Task not found")

    @app.exception_handler(CrossCompanyAccessError)
    async def handle_cross_company(request: Request, exc: CrossCompanyAccessError) -> JSONResponse:
        """Отдаёт 404 при обращении к задаче чужой компании.

        Именно 404, а не 403 — чтобы перебором id нельзя было выяснить,
        какие задачи существуют в других компаниях.
        """
        return _error_response(status.HTTP_404_NOT_FOUND, "Task not found")

    @app.exception_handler(UserNotFoundError)
    async def handle_user_not_found(request: Request, exc: UserNotFoundError) -> JSONResponse:
        """Отдаёт 404, если участник отсутствует в реплике или из другой компании."""
        return _error_response(
            status.HTTP_404_NOT_FOUND, "One or more participants not found in this company"
        )

    @app.exception_handler(InvalidStatusTransitionError)
    async def handle_invalid_transition(
        request: Request, exc: InvalidStatusTransitionError
    ) -> JSONResponse:
        """Отдаёт 409 при недопустимом переходе статуса."""
        return _error_response(status.HTTP_409_CONFLICT, "Invalid status transition")

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        """Отдаёт 500 на любое непредусмотренное исключение."""
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error")
