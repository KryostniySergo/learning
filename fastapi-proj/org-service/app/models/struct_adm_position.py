from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class StructAdmPosition(Base, TimestampMixin):
    """Связь между подразделением и должностью — какие должности доступны в узле."""

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    struct_adm_id: Mapped[PyUUID] = mapped_column(ForeignKey("struct_adm.id"), nullable=False)
    position_id: Mapped[PyUUID] = mapped_column(ForeignKey("position.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("struct_adm_id", "position_id", name="uq_struct_adm_positions_struct_adm_id_position_id"),
    )
