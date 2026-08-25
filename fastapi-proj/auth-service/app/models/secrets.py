from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Secrets(Base, TimestampMixin):
    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    password_hash: Mapped[str] = mapped_column(String(120), nullable=False)

    user_id: Mapped[PyUUID] = mapped_column(ForeignKey("user.id"), unique=True, nullable=False)
    account_id: Mapped[PyUUID] = mapped_column(ForeignKey("account.id"), unique=True, nullable=False)
