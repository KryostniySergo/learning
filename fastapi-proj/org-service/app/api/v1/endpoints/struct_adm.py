from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_user
from app.schemas.current_user import CurrentUser
from app.schemas.struct_adm import (
    AssignManagerRequest,
    CreateChildRequest,
    CreateRootRequest,
    DeleteSubtreeResponse,
    RenameRequest,
    StructAdmResponse,
)
from app.services.struct_adm_service import StructAdmService
from app.uow import UnitOfWork

router = APIRouter(prefix="/struct-adm", tags=["struct-adm"])

CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.post("/root", response_model=StructAdmResponse, status_code=status.HTTP_201_CREATED)
async def create_root(
    body: CreateRootRequest,
    current_user: CurrentUserDep,
) -> StructAdmResponse:
    """Создаёт корневое подразделение компании.

    Args:
        body (CreateRootRequest): название подразделения.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        StructAdmResponse: созданный узел оргструктуры.
    """
    async with UnitOfWork() as uow:
        node = await StructAdmService(uow).create_root(body.name, current_user)
        return StructAdmResponse.model_validate(node)


@router.post("/child", response_model=StructAdmResponse, status_code=status.HTTP_201_CREATED)
async def create_child(
    body: CreateChildRequest,
    current_user: CurrentUserDep,
) -> StructAdmResponse:
    """Создаёт дочернее подразделение под указанным родителем.

    Args:
        body (CreateChildRequest): id родителя и название нового подразделения.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        StructAdmResponse: созданный узел оргструктуры.
    """
    async with UnitOfWork() as uow:
        node = await StructAdmService(uow).create_child(body.parent_id, body.name, current_user)
        return StructAdmResponse.model_validate(node)


@router.patch("/{node_id}", response_model=StructAdmResponse)
async def rename(
    node_id: UUID,
    body: RenameRequest,
    current_user: CurrentUserDep,
) -> StructAdmResponse:
    """Переименовывает подразделение.

    Args:
        node_id (UUID): id подразделения.
        body (RenameRequest): новое название.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        StructAdmResponse: обновлённый узел.
    """
    async with UnitOfWork() as uow:
        node = await StructAdmService(uow).rename(node_id, body.name, current_user)
        return StructAdmResponse.model_validate(node)


@router.put("/{node_id}/manager", response_model=StructAdmResponse)
async def assign_manager(
    node_id: UUID,
    body: AssignManagerRequest,
    current_user: CurrentUserDep,
) -> StructAdmResponse:
    """Назначает руководителя подразделения.

    Args:
        node_id (UUID): id подразделения.
        body (AssignManagerRequest): id назначаемого руководителя.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        StructAdmResponse: обновлённый узел.
    """
    async with UnitOfWork() as uow:
        node = await StructAdmService(uow).assign_manager(node_id, body.manager_id, current_user)
        return StructAdmResponse.model_validate(node)


@router.delete("/{node_id}", response_model=DeleteSubtreeResponse)
async def delete_subtree(
    node_id: UUID,
    current_user: CurrentUserDep,
) -> DeleteSubtreeResponse:
    """Каскадно удаляет подразделение вместе со всем поддеревом.

    Args:
        node_id (UUID): id удаляемого подразделения.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        DeleteSubtreeResponse: количество удалённых узлов.
    """
    async with UnitOfWork() as uow:
        count = await StructAdmService(uow).delete_subtree(node_id, current_user)
        return DeleteSubtreeResponse(deleted_count=count)


@router.get("/", response_model=list[StructAdmResponse])
async def get_tree(current_user: CurrentUserDep) -> list[StructAdmResponse]:
    """Возвращает всю оргструктуру компании текущего пользователя.

    Args:
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        list[StructAdmResponse]: все узлы компании, отсортированные по пути.
    """
    async with UnitOfWork() as uow:
        nodes = await StructAdmService(uow).get_tree(current_user)
        return [StructAdmResponse.model_validate(node) for node in nodes]


@router.get("/{node_id}/subtree", response_model=list[StructAdmResponse])
async def get_subtree(
    node_id: UUID,
    current_user: CurrentUserDep,
) -> list[StructAdmResponse]:
    """Возвращает поддерево указанного подразделения.

    Args:
        node_id (UUID): id корня искомого поддерева.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        list[StructAdmResponse]: узлы поддерева, не включая сам узел.
    """
    async with UnitOfWork() as uow:
        nodes = await StructAdmService(uow).get_subtree(node_id, current_user)
        return [StructAdmResponse.model_validate(node) for node in nodes]
