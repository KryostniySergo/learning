import re
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column
from sqlalchemy.sql import func


def camel_to_snake(name: str) -> str:
    """camel_to_snake переводит название класса формата UsersPositions в user_position

    Args:
        name (str): Название класса

    Returns:
        str: Форматированное название класса
    """
    # вставляем "_" перед каждой заглавной буквой, которая не в начале строки
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


class Base(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: D105
        return camel_to_snake(cls.__name__)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
