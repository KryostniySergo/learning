from uuid import uuid4

from app.models.base import Base, TimestampMixin
from sqlalchemy import UUID, String
from sqlalchemy.orm import Mapped, mapped_column


class Company(Base, TimestampMixin):
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
