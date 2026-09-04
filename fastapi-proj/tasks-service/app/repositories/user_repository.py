from uuid import UUID

from sqlalchemy import select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def list_by_ids(self, user_ids: list[UUID]) -> list[User]:
        """Находит существующих неудалённых пользователей по списку идентификаторов.

        Args:
            user_ids (list[UUID]): идентификаторы для поиска.

        Returns:
            list[User]: найденные пользователи (может быть меньше, чем запрошено).
        """
        if not user_ids:
            return []
        result = await self.session.execute(
            select(User).where(User.id.in_(user_ids)).where(User.deleted_at.is_(None))
        )
        return list(result.scalars().all())
