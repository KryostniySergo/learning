from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TaskAssignee(Base, TimestampMixin):
    """Исполнитель задачи."""

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[PyUUID] = mapped_column(ForeignKey("task.id"), nullable=False)
    user_id: Mapped[PyUUID] = mapped_column(ForeignKey("user.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("task_id", "user_id", name="uq_task_assignee_task_id_user_id"),
    )
