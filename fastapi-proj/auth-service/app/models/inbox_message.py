from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import TIMESTAMP, UUID, String
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class InMessageStatus(str, Enum):
    RECEIVED = "received"
    PROCESSED = "processed"
    FAILED = "failed"


class InboxMessage(Base):
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(UUID, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100))
    consumer_name: Mapped[str] = mapped_column(String(100))  # какой обработчик/сервис это принял

    received_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    status: Mapped[InMessageStatus] = mapped_column(SqlEnum(InMessageStatus), default=InMessageStatus.RECEIVED)
