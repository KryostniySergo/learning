from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserPosition(Base):
    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[PyUUID] = mapped_column(ForeignKey("user.id"), nullable=False)
    position_id: Mapped[PyUUID] = mapped_column(ForeignKey("position.id"), nullable=False)
