from datetime import UTC, datetime
from enum import Enum
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import TIMESTAMP, UUID, DateTime, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SagaStatus(str, Enum):
    """Общий статус выполнения саги."""

    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"


class SagaStep(str, Enum):
    """Текущий шаг саги онбординга."""

    STARTED = "started"
    ORG_ASSIGN_SENT = "org_assign_sent"
    TASK_CREATE_SENT = "task_create_sent"
    COMPLETED = "completed"
    COMPENSATING_ORG = "compensating_org"
    COMPENSATING_INVITE = "compensating_invite"
    COMPENSATED = "compensated"


class SagaInstance(Base):
    """Состояние одного запущенного экземпляра саги онбординга."""

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    saga_type: Mapped[str] = mapped_column(String(100), default="employee_onboarding")

    employee_id: Mapped[PyUUID] = mapped_column(UUID, index=True)
    company_id: Mapped[PyUUID] = mapped_column(UUID)
    invite_id: Mapped[PyUUID] = mapped_column(UUID)
    struct_adm_id: Mapped[PyUUID | None] = mapped_column(UUID, nullable=True)
    position_id: Mapped[PyUUID | None] = mapped_column(UUID, nullable=True)

    current_step: Mapped[SagaStep] = mapped_column(SqlEnum(SagaStep), default=SagaStep.STARTED)
    status: Mapped[SagaStatus] = mapped_column(SqlEnum(SagaStatus), default=SagaStatus.RUNNING)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
