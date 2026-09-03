from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CreatePositionRequest(BaseModel):
    """Тело запроса на создание должности."""

    title: str


class RenamePositionRequest(BaseModel):
    """Тело запроса на переименование должности."""

    title: str


class LinkPositionRequest(BaseModel):
    """Тело запроса на привязку должности к подразделению."""

    position_id: UUID


class AssignUserRequest(BaseModel):
    """Тело запроса на назначение сотрудника на должность."""

    user_id: UUID


class PositionResponse(BaseModel):
    """Представление должности в ответах API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    company_id: UUID
    created_at: datetime


class StructAdmPositionResponse(BaseModel):
    """Представление привязки должности к подразделению."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    struct_adm_id: UUID
    position_id: UUID
    created_at: datetime


class UserPositionResponse(BaseModel):
    """Представление назначения сотрудника на должность."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    position_id: UUID
    created_at: datetime
