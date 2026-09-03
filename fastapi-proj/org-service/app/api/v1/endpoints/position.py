from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user
from app.schemas.current_user import CurrentUser
from app.schemas.position import (
    AssignUserRequest,
    CreatePositionRequest,
    LinkPositionRequest,
    PositionResponse,
    RenamePositionRequest,
    StructAdmPositionResponse,
    UserPositionResponse,
)
from app.services.position_service import PositionService
from app.uow import UnitOfWork

router = APIRouter(prefix="/positions", tags=["positions"])

CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.post("/", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
async def create_position(
    body: CreatePositionRequest,
    current_user: CurrentUserDep,
) -> PositionResponse:
    """Создаёт должность в компании текущего пользователя.

    Args:
        body (CreatePositionRequest): название должности.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        PositionResponse: созданная должность.
    """
    async with UnitOfWork() as uow:
        position = await PositionService(uow).create(body.title, current_user)
        return PositionResponse.model_validate(position)


@router.get("/", response_model=list[PositionResponse])
async def list_positions(current_user: CurrentUserDep) -> list[PositionResponse]:
    """Возвращает все должности компании текущего пользователя.

    Args:
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        list[PositionResponse]: должности компании.
    """
    async with UnitOfWork() as uow:
        positions = await PositionService(uow).list_positions(current_user)
        return [PositionResponse.model_validate(p) for p in positions]


@router.patch("/{position_id}", response_model=PositionResponse)
async def rename_position(
    position_id: UUID,
    body: RenamePositionRequest,
    current_user: CurrentUserDep,
) -> PositionResponse:
    """Переименовывает должность.

    Args:
        position_id (UUID): id должности.
        body (RenamePositionRequest): новое название.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        PositionResponse: обновлённая должность.
    """
    async with UnitOfWork() as uow:
        position = await PositionService(uow).rename(position_id, body.title, current_user)
        return PositionResponse.model_validate(position)


@router.delete("/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(position_id: UUID, current_user: CurrentUserDep) -> None:
    """Удаляет должность вместе со всеми её привязками и назначениями.

    Args:
        position_id (UUID): id должности.
        current_user (CurrentUser): контекст текущего пользователя.
    """
    async with UnitOfWork() as uow:
        await PositionService(uow).delete(position_id, current_user)


@router.post(
    "/struct-adm/{struct_adm_id}",
    response_model=StructAdmPositionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def link_position_to_struct_adm(
    struct_adm_id: UUID,
    body: LinkPositionRequest,
    current_user: CurrentUserDep,
) -> StructAdmPositionResponse:
    """Привязывает должность к подразделению.

    Args:
        struct_adm_id (UUID): id подразделения.
        body (LinkPositionRequest): id привязываемой должности.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        StructAdmPositionResponse: созданная привязка.
    """
    async with UnitOfWork() as uow:
        link = await PositionService(uow).link_to_struct_adm(struct_adm_id, body.position_id, current_user)
        return StructAdmPositionResponse.model_validate(link)


@router.delete("/struct-adm/{struct_adm_id}/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_position_from_struct_adm(
    struct_adm_id: UUID,
    position_id: UUID,
    current_user: CurrentUserDep,
) -> None:
    """Отвязывает должность от подразделения.

    Args:
        struct_adm_id (UUID): id подразделения.
        position_id (UUID): id должности.
        current_user (CurrentUser): контекст текущего пользователя.
    """
    async with UnitOfWork() as uow:
        await PositionService(uow).unlink_from_struct_adm(struct_adm_id, position_id, current_user)


@router.get("/struct-adm/{struct_adm_id}", response_model=list[StructAdmPositionResponse])
async def list_struct_adm_positions(
    struct_adm_id: UUID,
    current_user: CurrentUserDep,
) -> list[StructAdmPositionResponse]:
    """Возвращает должности, привязанные к подразделению.

    Args:
        struct_adm_id (UUID): id подразделения.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        list[StructAdmPositionResponse]: привязки подразделение-должность.
    """
    async with UnitOfWork() as uow:
        links = await PositionService(uow).list_struct_adm_positions(struct_adm_id, current_user)
        return [StructAdmPositionResponse.model_validate(link) for link in links]


@router.post(
    "/{position_id}/users",
    response_model=UserPositionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_user_to_position(
    position_id: UUID,
    body: AssignUserRequest,
    current_user: CurrentUserDep,
) -> UserPositionResponse:
    """Назначает сотрудника на должность.

    Args:
        position_id (UUID): id должности.
        body (AssignUserRequest): id назначаемого сотрудника.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        UserPositionResponse: созданное назначение.
    """
    async with UnitOfWork() as uow:
        assignment = await PositionService(uow).assign_user(body.user_id, position_id, current_user)
        return UserPositionResponse.model_validate(assignment)


@router.delete("/{position_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_user_from_position(
    position_id: UUID,
    user_id: UUID,
    current_user: CurrentUserDep,
) -> None:
    """Снимает сотрудника с должности.

    Args:
        position_id (UUID): id должности.
        user_id (UUID): id сотрудника.
        current_user (CurrentUser): контекст текущего пользователя.
    """
    async with UnitOfWork() as uow:
        await PositionService(uow).unassign_user(user_id, position_id, current_user)


@router.get("/users/{user_id}", response_model=list[UserPositionResponse])
async def list_user_positions(
    user_id: UUID,
    current_user: CurrentUserDep,
) -> list[UserPositionResponse]:
    """Возвращает должности, занимаемые сотрудником.

    Args:
        user_id (UUID): id сотрудника.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        list[UserPositionResponse]: назначения сотрудника.
    """
    async with UnitOfWork() as uow:
        assignments = await PositionService(uow).list_user_positions(user_id, current_user)
        return [UserPositionResponse.model_validate(a) for a in assignments]
