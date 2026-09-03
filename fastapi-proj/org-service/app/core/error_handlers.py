import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    CrossCompanyAccessError,
    NotAuthorizedError,
    ParentNotFoundError,
    PositionNotFoundError,
    StructAdmNotFoundError,
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

    Благодаря этому эндпоинты не нуждаются в try/except — доменные исключения
    из сервисного слоя автоматически превращаются в корректные HTTP-ответы.

    Args:
        app (FastAPI): экземпляр приложения, к которому привязываются обработчики.
    """

    @app.exception_handler(NotAuthorizedError)
    async def handle_not_authorized(request: Request, exc: NotAuthorizedError) -> JSONResponse:
        """Отдаёт 403, если у пользователя нет прав на операцию."""
        return _error_response(status.HTTP_403_FORBIDDEN, "Admin role required")

    @app.exception_handler(ParentNotFoundError)
    async def handle_parent_not_found(request: Request, exc: ParentNotFoundError) -> JSONResponse:
        """Отдаёт 404, если родительское подразделение не найдено."""
        return _error_response(status.HTTP_404_NOT_FOUND, "Parent struct adm not found")

    @app.exception_handler(StructAdmNotFoundError)
    async def handle_struct_adm_not_found(request: Request, exc: StructAdmNotFoundError) -> JSONResponse:
        """Отдаёт 404, если подразделение не найдено."""
        return _error_response(status.HTTP_404_NOT_FOUND, "Struct adm not found")

    @app.exception_handler(CrossCompanyAccessError)
    async def handle_cross_company(request: Request, exc: CrossCompanyAccessError) -> JSONResponse:
        """Отдаёт 404 при обращении к сущности чужой компании.

        Именно 404, а не 403 — чтобы перебором id нельзя было выяснить,
        какие сущности существуют в других компаниях.
        """
        return _error_response(status.HTTP_404_NOT_FOUND, "Struct adm not found")

    @app.exception_handler(UserNotFoundError)
    async def handle_user_not_found(request: Request, exc: UserNotFoundError) -> JSONResponse:
        """Отдаёт 404, если сотрудник отсутствует в локальной реплике."""
        return _error_response(status.HTTP_404_NOT_FOUND, "Employee not found")

    @app.exception_handler(PositionNotFoundError)
    async def handle_position_not_found(request: Request, exc: PositionNotFoundError) -> JSONResponse:
        """Отдаёт 404, если должность не найдена."""
        return _error_response(status.HTTP_404_NOT_FOUND, "Position not found")

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        """Отдаёт 500 на любое непредусмотренное исключение, не раскрывая деталей."""
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error")
