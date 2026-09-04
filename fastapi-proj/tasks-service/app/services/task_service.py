import logging
from datetime import datetime
from uuid import UUID, uuid4

from app.core.event_types import EventType
from app.core.exceptions import (
    CrossCompanyAccessError,
    InvalidStatusTransitionError,
    NotAuthorizedError,
    TaskNotFoundError,
    UserNotFoundError,
)
from app.core.outbox import build_outbox_message
from app.models.task import ALLOWED_STATUS_TRANSITIONS, Task, TaskStatus
from app.models.task_assignee import TaskAssignee
from app.models.task_watcher import TaskWatcher
from app.schemas.current_user import CurrentUser
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


class TaskService:
    """Бизнес-логика управления задачами."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Инициализирует сервис.

        Args:
            uow (UnitOfWork): единица работы, дающая доступ к репозиториям и транзакции.
        """
        self.uow = uow

    async def create(
        self,
        title: str,
        description: str | None,
        responsible_id: UUID,
        watcher_ids: list[UUID],
        assignee_ids: list[UUID],
        deadline: datetime | None,
        estimate_minutes: int | None,
        current_user: CurrentUser,
    ) -> Task:
        """Создаёт задачу, проверяя всех участников по локальной реплике.

        Args:
            title (str): заголовок задачи.
            description (str | None): описание задачи.
            responsible_id (UUID): ответственный за задачу.
            watcher_ids (list[UUID]): наблюдатели.
            assignee_ids (list[UUID]): исполнители.
            deadline (datetime | None): срок выполнения.
            estimate_minutes (int | None): оценка времени в минутах.
            current_user (CurrentUser): контекст текущего пользователя — становится автором.

        Returns:
            Task: созданная задача.

        Raises:
            UserNotFoundError: если кто-то из участников отсутствует в реплике
                или состоит в другой компании.
        """
        participants = {current_user.user_id, responsible_id, *watcher_ids, *assignee_ids}
        await self._validate_participants(participants, current_user)

        task = Task(
            id=uuid4(),
            title=title,
            description=description,
            company_id=current_user.company_id,
            author_id=current_user.user_id,
            responsible_id=responsible_id,
            deadline=deadline,
            estimate_minutes=estimate_minutes,
            status=TaskStatus.NEW,
        )
        self.uow.task.add(task)
        await self.uow.session.flush()

        for user_id in set(watcher_ids):
            self.uow.task_watcher.add(TaskWatcher(id=uuid4(), task_id=task.id, user_id=user_id))
        for user_id in set(assignee_ids):
            self.uow.task_assignee.add(TaskAssignee(id=uuid4(), task_id=task.id, user_id=user_id))

        await self.uow.commit()
        logger.info("task created: %s by %s", task.id, current_user.user_id)
        return task

    async def update(
        self,
        task_id: UUID,
        current_user: CurrentUser,
        title: str | None = None,
        description: str | None = None,
        responsible_id: UUID | None = None,
        deadline: datetime | None = None,
        estimate_minutes: int | None = None,
    ) -> Task:
        """Обновляет поля задачи. Передаются только изменяемые поля.

        Args:
            task_id (UUID): идентификатор задачи.
            current_user (CurrentUser): контекст текущего пользователя.
            title (str | None): новый заголовок.
            description (str | None): новое описание.
            responsible_id (UUID | None): новый ответственный.
            deadline (datetime | None): новый срок.
            estimate_minutes (int | None): новая оценка времени.

        Returns:
            Task: обновлённая задача.

        Raises:
            TaskNotFoundError: если задача не найдена.
            CrossCompanyAccessError: если задача принадлежит другой компании.
            NotAuthorizedError: если пользователь не автор, не ответственный и не админ.
            UserNotFoundError: если новый ответственный отсутствует в реплике.
        """
        task = await self._get_editable_task(task_id, current_user)

        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if deadline is not None:
            task.deadline = deadline
        if estimate_minutes is not None:
            task.estimate_minutes = estimate_minutes
        if responsible_id is not None:
            await self._validate_participants({responsible_id}, current_user)
            task.responsible_id = responsible_id

        await self.uow.commit()
        logger.info("task updated: %s by %s", task_id, current_user.user_id)
        return task

    async def change_status(
        self, task_id: UUID, new_status: TaskStatus, current_user: CurrentUser
    ) -> Task:
        """Меняет статус задачи с проверкой допустимости перехода.

        Публикует событие task.status_changed через transactional outbox.

        Args:
            task_id (UUID): идентификатор задачи.
            new_status (TaskStatus): целевой статус.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            Task: задача с обновлённым статусом.

        Raises:
            TaskNotFoundError: если задача не найдена.
            CrossCompanyAccessError: если задача принадлежит другой компании.
            NotAuthorizedError: если пользователь не автор, не ответственный и не админ.
            InvalidStatusTransitionError: если переход из текущего статуса недопустим.
        """
        task = await self._get_editable_task(task_id, current_user)

        old_status = task.status
        if new_status not in ALLOWED_STATUS_TRANSITIONS[old_status]:
            logger.warning(
                "invalid transition %s -> %s for task %s", old_status, new_status, task_id
            )
            raise InvalidStatusTransitionError

        task.status = new_status

        self.uow.outbox.add(
            build_outbox_message(
                event_type=EventType.TASK_STATUS_CHANGED,
                aggregate_id=task.id,
                payload={
                    "task_id": str(task.id),
                    "company_id": str(task.company_id),
                    "old_status": old_status.value,
                    "new_status": new_status.value,
                    "changed_by": str(current_user.user_id),
                    "responsible_id": str(task.responsible_id),
                },
            )
        )

        await self.uow.commit()
        logger.info("task %s status changed %s -> %s", task_id, old_status, new_status)
        return task

    async def delete(self, task_id: UUID, current_user: CurrentUser) -> None:
        """Мягко удаляет задачу вместе с её наблюдателями и исполнителями.

        Args:
            task_id (UUID): идентификатор задачи.
            current_user (CurrentUser): контекст текущего пользователя.

        Raises:
            TaskNotFoundError: если задача не найдена.
            CrossCompanyAccessError: если задача принадлежит другой компании.
            NotAuthorizedError: если пользователь не автор, не ответственный и не админ.
        """
        task = await self._get_editable_task(task_id, current_user)
        deleted_at = datetime.now()

        for watcher in await self.uow.task_watcher.list_by_task(task_id):
            watcher.deleted_at = deleted_at
        for assignee in await self.uow.task_assignee.list_by_task(task_id):
            assignee.deleted_at = deleted_at

        task.deleted_at = deleted_at
        await self.uow.commit()
        logger.info("task deleted: %s by %s", task_id, current_user.user_id)

    async def get(self, task_id: UUID, current_user: CurrentUser) -> Task:
        """Возвращает задачу, если она принадлежит компании пользователя.

        Args:
            task_id (UUID): идентификатор задачи.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            Task: найденная задача.

        Raises:
            TaskNotFoundError: если задача не найдена.
            CrossCompanyAccessError: если задача принадлежит другой компании.
        """
        return await self._get_owned_task(task_id, current_user)

    async def list_tasks(
        self,
        current_user: CurrentUser,
        status: TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        """Возвращает задачи компании текущего пользователя.

        Args:
            current_user (CurrentUser): контекст текущего пользователя.
            status (TaskStatus | None): фильтр по статусу.
            limit (int): размер страницы.
            offset (int): смещение для пагинации.

        Returns:
            list[Task]: задачи компании, новые первыми.
        """
        return await self.uow.task.list_by_company(
            current_user.company_id, status=status, limit=limit, offset=offset
        )

    async def get_participants(self, task_id: UUID) -> tuple[list[UUID], list[UUID]]:
        """Возвращает идентификаторы наблюдателей и исполнителей задачи.

        Args:
            task_id (UUID): идентификатор задачи.

        Returns:
            tuple[list[UUID], list[UUID]]: списки id наблюдателей и исполнителей.
        """
        watchers = await self.uow.task_watcher.list_by_task(task_id)
        assignees = await self.uow.task_assignee.list_by_task(task_id)
        return [w.user_id for w in watchers], [a.user_id for a in assignees]

    async def _validate_participants(
        self, user_ids: set[UUID], current_user: CurrentUser
    ) -> None:
        """Проверяет, что все указанные пользователи есть в реплике и в той же компании.

        Args:
            user_ids (set[UUID]): идентификаторы проверяемых пользователей.
            current_user (CurrentUser): контекст текущего пользователя.

        Raises:
            UserNotFoundError: если кто-то отсутствует в реплике либо из другой компании.
        """
        found = await self.uow.user.list_by_ids(list(user_ids))
        found_ids = {user.id for user in found}

        missing = user_ids - found_ids
        if missing:
            logger.warning("participants not found in replica: %s", missing)
            raise UserNotFoundError

        foreign = {user.id for user in found if user.company_id != current_user.company_id}
        if foreign:
            logger.warning("participants from another company: %s", foreign)
            raise UserNotFoundError

    async def _get_owned_task(self, task_id: UUID, current_user: CurrentUser) -> Task:
        """Загружает задачу и проверяет принадлежность компании пользователя.

        Args:
            task_id (UUID): идентификатор задачи.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            Task: найденная задача.

        Raises:
            TaskNotFoundError: если задача не найдена или удалена.
            CrossCompanyAccessError: если задача принадлежит другой компании.
        """
        task = await self.uow.task.get_by_id(task_id)
        if task is None or task.deleted_at is not None:
            raise TaskNotFoundError
        if task.company_id != current_user.company_id:
            logger.warning(
                "cross-company access attempt: user=%s task=%s", current_user.user_id, task_id
            )
            raise CrossCompanyAccessError
        return task

    async def _get_editable_task(self, task_id: UUID, current_user: CurrentUser) -> Task:
        """Загружает задачу и проверяет право текущего пользователя её изменять.

        Изменять задачу может её автор, ответственный или администратор компании.

        Args:
            task_id (UUID): идентификатор задачи.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            Task: найденная задача.

        Raises:
            TaskNotFoundError: если задача не найдена или удалена.
            CrossCompanyAccessError: если задача принадлежит другой компании.
            NotAuthorizedError: если пользователь не автор, не ответственный и не админ.
        """
        task = await self._get_owned_task(task_id, current_user)

        is_participant = current_user.user_id in (task.author_id, task.responsible_id)
        if not is_participant and not current_user.is_admin:
            logger.warning(
                "edit denied: user=%s is neither author nor responsible for task %s",
                current_user.user_id,
                task_id,
            )
            raise NotAuthorizedError

        return task
