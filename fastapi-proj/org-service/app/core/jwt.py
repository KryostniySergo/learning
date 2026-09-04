import jwt
from app.core.config import settings


class InvalidTokenError(Exception):
    """Исключение, если JWT невалиден, повреждён или истёк."""


def decode_access_token(token: str) -> dict:
    """Проверяет подпись и срок действия JWT, возвращая его payload.

    Токен выпускается auth-service; org-service только проверяет его тем же
    секретом, без обращения к auth-service по сети.

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
