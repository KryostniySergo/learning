import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AccountAlreadyExistsError,
    EmployeeAlreadyInCompanyError,
    InvalidCredentialsError,
    InviteAccountMismatchError,
    InviteExpiredError,
    InviteInvalidStatusError,
    InviteNotFoundError,
    NotAuthenticatedError,
    NotAuthorizedError,
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

    @app.exception_handler(AccountAlreadyExistsError)
    async def handle_account_exists(request: Request, exc: AccountAlreadyExistsError) -> JSONResponse:
        """Отдаёт 409, если почта уже занята."""
        return _error_response(status.HTTP_409_CONFLICT, "Account already exists")

    @app.exception_handler(InviteNotFoundError)
    async def handle_invite_not_found(request: Request, exc: InviteNotFoundError) -> JSONResponse:
        """Отдаёт 404, если инвайт не найден."""
        return _error_response(status.HTTP_404_NOT_FOUND, "Invite not found")

    @app.exception_handler(InviteAccountMismatchError)
    async def handle_invite_mismatch(request: Request, exc: InviteAccountMismatchError) -> JSONResponse:
        """Отдаёт 404, если токен не относится к указанной почте.

        Ответ намеренно совпадает с 'инвайт не найден' — чтобы перебором токенов
        нельзя было выяснить, какие почты зарегистрированы в системе.
        """
        return _error_response(status.HTTP_404_NOT_FOUND, "Invite not found")

    @app.exception_handler(InviteExpiredError)
    async def handle_invite_expired(request: Request, exc: InviteExpiredError) -> JSONResponse:
        """Отдаёт 410, если срок действия инвайта истёк."""
        return _error_response(status.HTTP_410_GONE, "Invite expired")

    @app.exception_handler(InviteInvalidStatusError)
    async def handle_invite_invalid_status(request: Request, exc: InviteInvalidStatusError) -> JSONResponse:
        """Отдаёт 409, если инвайт не в том статусе для запрошенного перехода."""
        return _error_response(status.HTTP_409_CONFLICT, "Invite is not in a valid state for this action")

    @app.exception_handler(InvalidCredentialsError)
    async def handle_invalid_credentials(request: Request, exc: InvalidCredentialsError) -> JSONResponse:
        """Отдаёт 401 при неверной паре почта/пароль."""
        return _error_response(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    @app.exception_handler(NotAuthenticatedError)
    async def handle_not_authenticated(request: Request, exc: NotAuthenticatedError) -> JSONResponse:
        """Отдаёт 401, если запрос без валидного токена."""
        return _error_response(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    @app.exception_handler(NotAuthorizedError)
    async def handle_not_authorized(request: Request, exc: NotAuthorizedError) -> JSONResponse:
        """Отдаёт 403, если у пользователя нет прав на операцию."""
        return _error_response(status.HTTP_403_FORBIDDEN, "Admin role required")

    @app.exception_handler(EmployeeAlreadyInCompanyError)
    async def handle_employee_already_in_company(request: Request, exc: EmployeeAlreadyInCompanyError) -> JSONResponse:
        """Отдаёт 409, если сотрудник уже состоит в этой компании."""
        return _error_response(status.HTTP_409_CONFLICT, "Employee already in this company")

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        """Отдаёт 500 на любое непредусмотренное исключение, не раскрывая деталей."""
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error")

    @app.exception_handler(UserNotFoundError)
    async def handle_user_not_found(request: Request, exc: UserNotFoundError) -> JSONResponse:
        """Отдаёт 500 — ситуация означает рассогласованность данных, а не ошибку клиента."""
        return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error")
