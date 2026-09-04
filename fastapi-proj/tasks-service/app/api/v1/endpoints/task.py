from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_current_user
from app.models.task import TaskStatus
from app.schemas.current_user import CurrentUser
from app.schemas.task import (
    ChangeStatusRequest,
    CreateTaskRequest,
    TaskDetailResponse,
    TaskResponse,
    UpdateTaskRequest,
)
from app.services.task_service import TaskService
from app.uow import UnitOfWork

router = APIRouter(prefix="/tasks", tags=["tasks"])

CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(body: CreateTaskRequest, current_user: CurrentUserDep) -> TaskResponse:
    """Создаёт задачу. Автором становится текущий пользователь.

    Args:
        body (CreateTaskRequest): данные задачи и её участники.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        TaskResponse: созданная задача.
    """
    async with UnitOfWork() as uow:
        task = await TaskService(uow).create(
            title=body.title,
            description=body.description,
            responsible_id=body.responsible_id,
            watcher_ids=body.watcher_ids,
            assignee_ids=body.assignee_ids,
            deadline=body.deadline,
            estimate_minutes=body.estimate_minutes,
            current_user=current_user,
        )
        return TaskResponse.model_validate(task)


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    current_user: CurrentUserDep,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TaskResponse]:
    """Возвращает задачи компании текущего пользователя.

    Args:
        current_user (CurrentUser): контекст текущего пользователя.
        task_status (TaskStatus | None): фильтр по статусу.
        limit (int): размер страницы.
        offset (int): смещение для пагинации.

    Returns:
        list[TaskResponse]: задачи компании, новые первыми.
    """
    async with UnitOfWork() as uow:
        tasks = await TaskService(uow).list_tasks(
            current_user, status=task_status, limit=limit, offset=offset
        )
        return [TaskResponse.model_validate(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: UUID, current_user: CurrentUserDep) -> TaskDetailResponse:
    """Возвращает задачу вместе со списками наблюдателей и исполнителей.

    Args:
        task_id (UUID): идентификатор задачи.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        TaskDetailResponse: задача с участниками.
    """
    async with UnitOfWork() as uow:
        service = TaskService(uow)
        task = await service.get(task_id, current_user)
        watcher_ids, assignee_ids = await service.get_participants(task_id)
        return TaskDetailResponse(
            **TaskResponse.model_validate(task).model_dump(),
            watcher_ids=watcher_ids,
            assignee_ids=assignee_ids,
        )


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID, body: UpdateTaskRequest, current_user: CurrentUserDep
) -> TaskResponse:
    """Изменяет поля задачи.

    Args:
        task_id (UUID): идентификатор задачи.
        body (UpdateTaskRequest): изменяемые поля.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        TaskResponse: обновлённая задача.
    """
    async with UnitOfWork() as uow:
        task = await TaskService(uow).update(
            task_id=task_id,
            current_user=current_user,
            title=body.title,
            description=body.description,
            responsible_id=body.responsible_id,
            deadline=body.deadline,
            estimate_minutes=body.estimate_minutes,
        )
        return TaskResponse.model_validate(task)


@router.put("/{task_id}/status", response_model=TaskResponse)
async def change_status(
    task_id: UUID, body: ChangeStatusRequest, current_user: CurrentUserDep
) -> TaskResponse:
    """Меняет статус задачи и публикует событие task.status_changed.

    Args:
        task_id (UUID): идентификатор задачи.
        body (ChangeStatusRequest): целевой статус.
        current_user (CurrentUser): контекст текущего пользователя.

    Returns:
        TaskResponse: задача с новым статусом.
    """
    async with UnitOfWork() as uow:
        task = await TaskService(uow).change_status(task_id, body.status, current_user)
        return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: UUID, current_user: CurrentUserDep) -> None:
    """Удаляет задачу вместе с её участниками.

    Args:
        task_id (UUID): идентификатор задачи.
        current_user (CurrentUser): контекст текущего пользователя.
    """
    async with UnitOfWork() as uow:
        await TaskService(uow).delete(task_id, current_user)
