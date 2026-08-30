from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Position(Base, TimestampMixin):
    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255))
    company_id: Mapped[PyUUID] = mapped_column(ForeignKey("company.id"), nullable=False)
