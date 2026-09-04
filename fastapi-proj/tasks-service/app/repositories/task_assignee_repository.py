from uuid import UUID

from sqlalchemy import select

from app.models.task_assignee import TaskAssignee
from app.repositories.base import BaseRepository


class TaskAssigneeRepository(BaseRepository[TaskAssignee]):
    model = TaskAssignee

    async def list_by_task(self, task_id: UUID) -> list[TaskAssignee]:
        """Находит действующих исполнителей задачи.

        Args:
            task_id (UUID): идентификатор задачи.

        Returns:
            list[TaskAssignee]: исполнители задачи.
        """
        result = await self.session.execute(
            select(TaskAssignee)
            .where(TaskAssignee.task_id == task_id)
            .where(TaskAssignee.deleted_at.is_(None))
        )
        return list(result.scalars().all())
