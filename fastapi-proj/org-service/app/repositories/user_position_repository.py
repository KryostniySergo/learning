from uuid import UUID as PyUUID

from sqlalchemy import select

from app.models.user_position import UserPosition
from app.repositories.base import BaseRepository


class UserPositionRepository(BaseRepository[UserPosition]):
    model = UserPosition

    async def get_by_user(self, user_id: PyUUID) -> list[UserPosition]:
        """Находит все действующие назначения сотрудника на должности.

        Args:
            user_id (PyUUID): id сотрудника.

        Returns:
            list[UserPosition]: назначения сотрудника.
        """
        result = await self.session.execute(
            select(UserPosition).where(UserPosition.user_id == user_id).where(UserPosition.deleted_at.is_(None))
        )
        return list(result.scalars().all())

    async def get_by_position(self, position_id: PyUUID) -> list[UserPosition]:
        """Находит всех сотрудников, назначенных на должность.

        Args:
            position_id (PyUUID): id должности.

        Returns:
            list[UserPosition]: назначения на эту должность.
        """
        result = await self.session.execute(
            select(UserPosition).where(UserPosition.position_id == position_id).where(UserPosition.deleted_at.is_(None))
        )
        return list(result.scalars().all())

    async def get_link(self, user_id: PyUUID, position_id: PyUUID) -> UserPosition | None:
        """Находит конкретное назначение сотрудника на должность.

        Args:
            user_id (PyUUID): id сотрудника.
            position_id (PyUUID): id должности.

        Returns:
            UserPosition | None: найденное назначение, либо None.
        """
        result = await self.session.execute(
            select(UserPosition)
            .where(UserPosition.user_id == user_id)
            .where(UserPosition.position_id == position_id)
            .where(UserPosition.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()
