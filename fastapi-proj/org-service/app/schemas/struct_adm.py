from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class CreateRootRequest(BaseModel):
    """Тело запроса на создание корневого подразделения."""

    name: str


class CreateChildRequest(BaseModel):
    """Тело запроса на создание дочернего подразделения."""

    parent_id: UUID
    name: str


class RenameRequest(BaseModel):
    """Тело запроса на переименование подразделения."""

    name: str


class AssignManagerRequest(BaseModel):
    """Тело запроса на назначение руководителя подразделения."""

    manager_id: UUID


class StructAdmResponse(BaseModel):
    """Представление узла оргструктуры в ответах API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    path: str
    company_id: UUID
    manager_id: UUID | None
    created_at: datetime

    @field_validator("path", mode="before")
    @classmethod
    def coerce_path_to_str(cls, value: Any) -> str:
        """Приводит Ltree-объект из ORM-модели к строке.

        Args:
            value (Any): значение path — объект Ltree либо уже строка.

        Returns:
            str: строковое представление пути.
        """
        return str(value)


class DeleteSubtreeResponse(BaseModel):
    """Ответ на удаление подразделения вместе с поддеревом."""

    deleted_count: int
