from uuid import UUID

from pydantic import BaseModel


class AssignEmployeeCommand(BaseModel):
    """Команда привязать сотрудника к подразделению и должности."""

    saga_id: UUID
    employee_id: UUID
    company_id: UUID
    struct_adm_id: UUID
    position_id: UUID | None = None


class UnassignEmployeeCommand(BaseModel):
    """Команда откатить привязку сотрудника — компенсация."""

    saga_id: UUID
    employee_id: UUID
    struct_adm_id: UUID
    position_id: UUID | None = None
