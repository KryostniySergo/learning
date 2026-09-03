from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class Role(str, Enum):
    """Роль пользователя в компании. Значения синхронизированы с auth-service."""

    ADMIN = "admin"
    USER = "user"


class CurrentUser(BaseModel):
    """Контекст текущего пользователя, извлечённый из JWT.

    Не хранится в БД org-service — приходит с каждым запросом в токене,
    поэтому всегда актуален (в пределах TTL токена) в отличие от реплики.
    """

    user_id: UUID
    company_id: UUID
    role: Role

    @property
    def is_admin(self) -> bool:
        """Проверяет, является ли пользователь администратором своей компании.

        Returns:
            bool: True, если роль пользователя — ADMIN.
        """
        return self.role is Role.ADMIN
