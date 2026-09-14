import re
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


def camel_to_snake(name: str) -> str:
    """Преобразует CamelCase в snake_case для имён таблиц.

    Args:
        name (str): имя класса модели.

    Returns:
        str: имя таблицы в snake_case.
    """
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


class Base(DeclarativeBase):
    """Базовый класс для SQLAlchemy ORM моделей."""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return camel_to_snake(cls.__name__)


class TimestampMixin:
    """Миксин с временными метками для всех моделей."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
