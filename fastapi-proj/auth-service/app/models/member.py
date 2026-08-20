from enum import Enum
from uuid import uuid4

from app.models.base import Base, TimestampMixin
from sqlalchemy import UUID, ForeignKey
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column


class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"


class Member(Base, TimestampMixin):
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("user.id"))
    company_id: Mapped[UUID] = mapped_column(ForeignKey("company.id"))

    role: Mapped[Role] = mapped_column(SqlEnum(Role))
