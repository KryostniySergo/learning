from datetime import datetime
from enum import Enum
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TaskStatus(str, Enum):
    """Статус задачи."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


ALLOWED_STATUS_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.NEW: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.IN_PROGRESS: {TaskStatus.DONE, TaskStatus.CANCELLED},
    TaskStatus.DONE: set(),
    TaskStatus.CANCELLED: set(),
}


class Task(Base, TimestampMixin):
    """Задача, поставленная сотруднику компании."""

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    company_id: Mapped[PyUUID] = mapped_column(ForeignKey("company.id"), nullable=False)
    author_id: Mapped[PyUUID] = mapped_column(ForeignKey("user.id"), nullable=False)
    responsible_id: Mapped[PyUUID] = mapped_column(ForeignKey("user.id"), nullable=False)

    deadline: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[TaskStatus] = mapped_column(SqlEnum(TaskStatus), default=TaskStatus.NEW)
    estimate_minutes: Mapped[int | None] = mapped_column(nullable=True)
