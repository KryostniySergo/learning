from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Company(Base, TimestampMixin):
    """Локальная реплика компании, получаемая из событий auth-service."""

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
