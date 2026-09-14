from enum import Enum
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Role(str, Enum):
    """Роль пользователя в компании (ADMIN или USER)."""

    ADMIN = "admin"
    USER = "user"


class Member(Base, TimestampMixin):
    """Членство сотрудника в компании (привязка пользователя к компании)."""

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)

    user_id: Mapped[PyUUID] = mapped_column(ForeignKey("user.id"))
    company_id: Mapped[PyUUID] = mapped_column(ForeignKey("company.id"))

    role: Mapped[Role] = mapped_column(SqlEnum(Role))
