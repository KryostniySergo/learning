from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import NotAuthenticatedError
from app.core.jwt import InvalidTokenError, decode_access_token
from app.schemas.current_user import CurrentUser

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> CurrentUser:
    """Извлекает и валидирует контекст пользователя из JWT.

    Args:
        credentials (HTTPAuthorizationCredentials | None): Bearer-токен из заголовка.

    Returns:
        CurrentUser: контекст пользователя.

    Raises:
        NotAuthenticatedError: если заголовок отсутствует или токен невалиден.
    """
    if credentials is None:
        raise NotAuthenticatedError

    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise NotAuthenticatedError from exc

    return CurrentUser(
        user_id=payload["sub"],
        company_id=payload["company_id"],
        role=payload["role"],
    )
