from datetime import datetime
from enum import Enum
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import INT, TIMESTAMP, UUID, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OutboxMessageStatus(str, Enum):
    """Статус доставки исходящего события в Kafka."""

    CREATED = "created"
    SENT = "sent"
    FAILED = "failed"


class OutboxMessage(Base):
    """Исходящее событие, ожидающее публикации в Kafka."""

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    event_id: Mapped[PyUUID] = mapped_column(UUID)
    event_type: Mapped[str] = mapped_column(String(100))
    aggregate_id: Mapped[PyUUID] = mapped_column(UUID)

    occurred_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    payload: Mapped[dict] = mapped_column(JSONB)

    status: Mapped[OutboxMessageStatus] = mapped_column(
        SqlEnum(OutboxMessageStatus), default=OutboxMessageStatus.CREATED
    )
    retry_count: Mapped[int] = mapped_column(INT, default=0)
