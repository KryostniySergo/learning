from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class UserPosition(Base, TimestampMixin):
    """Связь сотрудника с занимаемой должностью."""

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[PyUUID] = mapped_column(ForeignKey("user.id"), nullable=False)
    position_id: Mapped[PyUUID] = mapped_column(ForeignKey("position.id"), nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "position_id", name="uq_user_position_user_id_position_id"),)
