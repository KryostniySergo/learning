from datetime import datetime
from enum import Enum
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import TIMESTAMP, UUID, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class InboxMessageStatus(str, Enum):
    """Статус обработки входящего события."""

    RECEIVED = "received"
    PROCESSED = "processed"
    FAILED = "failed"


class InboxMessage(Base):
    """Отметка об обработанном входящем событии — защита от повторной обработки."""

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    event_id: Mapped[PyUUID] = mapped_column(UUID, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100))
    consumer_name: Mapped[str] = mapped_column(String(100))

    received_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    status: Mapped[InboxMessageStatus] = mapped_column(
        SqlEnum(InboxMessageStatus), default=InboxMessageStatus.RECEIVED
    )
