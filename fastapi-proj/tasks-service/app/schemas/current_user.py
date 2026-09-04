from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class Role(str, Enum):
    """Роль пользователя в компании."""

    ADMIN = "admin"
    USER = "user"


class CurrentUser(BaseModel):
    """Контекст текущего пользователя, извлечённый из JWT."""

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
