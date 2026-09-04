from uuid import UUID

from sqlalchemy import select

from app.models.task_watcher import TaskWatcher
from app.repositories.base import BaseRepository


class TaskWatcherRepository(BaseRepository[TaskWatcher]):
    model = TaskWatcher

    async def list_by_task(self, task_id: UUID) -> list[TaskWatcher]:
        """Находит действующих наблюдателей задачи.

        Args:
            task_id (UUID): идентификатор задачи.

        Returns:
            list[TaskWatcher]: наблюдатели задачи.
        """
        result = await self.session.execute(
            select(TaskWatcher)
            .where(TaskWatcher.task_id == task_id)
            .where(TaskWatcher.deleted_at.is_(None))
        )
        return list(result.scalars().all())
