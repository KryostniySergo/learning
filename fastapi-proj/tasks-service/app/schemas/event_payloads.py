from uuid import UUID

from pydantic import BaseModel


class CompanyCreatedPayload(BaseModel):
    """Payload события company.created."""

    company_id: UUID
    name: str


class EmployeeCreatedPayload(BaseModel):
    """Payload события employee.created."""

    employee_id: UUID
    name: str
    surname: str
    company_id: UUID
