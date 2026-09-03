from uuid import UUID as PyUUID

from sqlalchemy import select

from app.models.position import Position
from app.repositories.base import BaseRepository


class PositionRepository(BaseRepository[Position]):
    model = Position

    async def get_by_company(self, company_id: PyUUID) -> list[Position]:
        """Находит все не удалённые должности компании.

        Args:
            company_id (PyUUID): id компании.

        Returns:
            list[Position]: должности компании, отсортированные по названию.
        """
        result = await self.session.execute(
            select(Position)
            .where(Position.company_id == company_id)
            .where(Position.deleted_at.is_(None))
            .order_by(Position.title)
        )
        return list(result.scalars().all())
