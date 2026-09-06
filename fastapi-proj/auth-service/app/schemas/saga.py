from uuid import UUID

from pydantic import BaseModel


class EmployeeRegisteredPayload(BaseModel):
    """Payload события employee.registered — стартового сигнала саги."""

    employee_id: UUID
    company_id: UUID
    invite_id: UUID
    struct_adm_id: UUID | None = None
    position_id: UUID | None = None


class SagaReplyPayload(BaseModel):
    """Общий payload ответа исполнителя на команду саги."""

    saga_id: UUID
    employee_id: UUID
    error: str | None = None
