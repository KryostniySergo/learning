from datetime import datetime, timedelta
from enum import Enum
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import TIMESTAMP, ForeignKey, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class InviteStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


def default_expiry() -> datetime:
    """default_expiry Возвращает стандартное время истечения срока токена

    Returns:
        datetime: Стандартное время истечения срока токена
    """
    return datetime.now() + timedelta(days=14)


class Invite(Base, TimestampMixin):
    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    status: Mapped[InviteStatus] = mapped_column(SqlEnum(InviteStatus), default=InviteStatus.CREATED)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=default_expiry)

    user_id: Mapped[PyUUID | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    account_id: Mapped[PyUUID] = mapped_column(ForeignKey("account.id"), nullable=False)
