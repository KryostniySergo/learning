from uuid import UUID

from sqlalchemy import select

from app.models.saga_instance import SagaInstance, SagaStatus
from app.repositories.base import BaseRepository


class SagaInstanceRepository(BaseRepository[SagaInstance]):
    model = SagaInstance

    async def get_running_by_employee(self, employee_id: UUID) -> SagaInstance | None:
        """Находит незавершённую сагу онбординга для сотрудника.

        Args:
            employee_id (UUID): идентификатор сотрудника.

        Returns:
            SagaInstance | None: активная сага, либо None.
        """
        result = await self.session.execute(
            select(SagaInstance)
            .where(SagaInstance.employee_id == employee_id)
            .where(SagaInstance.status.in_([SagaStatus.RUNNING, SagaStatus.COMPENSATING]))
            .order_by(SagaInstance.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
