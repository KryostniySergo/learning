from uuid import UUID

from pydantic import BaseModel


class CreateWelcomeTaskCommand(BaseModel):
    """Команда создать приветственную задачу для нового сотрудника."""

    saga_id: UUID
    employee_id: UUID
    company_id: UUID
