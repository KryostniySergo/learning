from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskStatus


class CreateTaskRequest(BaseModel):
    """Тело запроса на создание задачи."""

    title: str
    description: str | None = None
    responsible_id: UUID
    watcher_ids: list[UUID] = Field(default_factory=list)
    assignee_ids: list[UUID] = Field(default_factory=list)
    deadline: datetime | None = None
    estimate_minutes: int | None = None


class UpdateTaskRequest(BaseModel):
    """Тело запроса на изменение задачи. Переданы только изменяемые поля."""

    title: str | None = None
    description: str | None = None
    responsible_id: UUID | None = None
    deadline: datetime | None = None
    estimate_minutes: int | None = None


class ChangeStatusRequest(BaseModel):
    """Тело запроса на смену статуса задачи."""

    status: TaskStatus


class TaskResponse(BaseModel):
    """Представление задачи в ответах API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    company_id: UUID
    author_id: UUID
    responsible_id: UUID
    deadline: datetime | None
    status: TaskStatus
    estimate_minutes: int | None
    created_at: datetime


class TaskDetailResponse(TaskResponse):
    """Задача вместе со списками наблюдателей и исполнителей."""

    watcher_ids: list[UUID]
    assignee_ids: list[UUID]
