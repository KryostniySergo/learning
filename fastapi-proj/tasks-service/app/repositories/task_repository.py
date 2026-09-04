from uuid import UUID

from sqlalchemy import select

from app.models.task import Task, TaskStatus
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    model = Task

    async def list_by_company(
        self,
        company_id: UUID,
        status: TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        """Находит задачи компании с необязательной фильтрацией по статусу.

        Args:
            company_id (UUID): идентификатор компании.
            status (TaskStatus | None): статус для фильтрации, либо None для всех.
            limit (int): максимальное количество записей.
            offset (int): смещение для пагинации.

        Returns:
            list[Task]: задачи компании, новые первыми.
        """
        query = (
            select(Task)
            .where(Task.company_id == company_id)
            .where(Task.deleted_at.is_(None))
        )
        if status is not None:
            query = query.where(Task.status == status)
        query = query.order_by(Task.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())
