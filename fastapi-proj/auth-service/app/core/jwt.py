from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.core.config import settings


class InvalidTokenError(Exception):
    """Исключение, если JWT невалиден, повреждён или истёк."""


def create_access_token(user_id: UUID, company_id: UUID, role: str) -> str:
    """Создаёт JWT с данными пользователя для последующей авторизации.

    Args:
        user_id (UUID): идентификатор пользователя.
        company_id (UUID): идентификатор компании, в которой он состоит.
        role (str): роль пользователя в этой компании.

    Returns:
        str: подписанный JWT.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "company_id": str(company_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Проверяет подпись и срок действия JWT, возвращая его payload.

    Args:
        token (str): JWT из заголовка Authorization.

    Returns:
        dict: полезная нагрузка токена.

    Raises:
        InvalidTokenError: если токен невалиден, повреждён или истёк.
    """
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError from exc
