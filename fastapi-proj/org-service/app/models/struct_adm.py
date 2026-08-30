from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_utils import Ltree, LtreeType

from app.models.base import Base, TimestampMixin


class StructAdm(Base, TimestampMixin):
    """Узел иерархии организационной структуры компании (дерево через ltree)."""

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    path: Mapped[Ltree] = mapped_column(LtreeType, nullable=False, unique=True)
    company_id: Mapped[PyUUID] = mapped_column(ForeignKey("company.id"), nullable=False)
    manager_id: Mapped[PyUUID | None] = mapped_column(ForeignKey("user.id"), nullable=True)
