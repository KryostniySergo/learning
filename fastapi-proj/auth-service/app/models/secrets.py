from uuid import uuid4

from sqlalchemy import UUID, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Secrets(Base, TimestampMixin):
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    password_hash: Mapped[str] = mapped_column(String(120), nullable=False)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"), unique=True, nullable=False)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("account.id"), unique=True, nullable=False)
