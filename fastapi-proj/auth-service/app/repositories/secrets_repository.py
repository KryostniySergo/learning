from uuid import UUID

from sqlalchemy import select

from app.models.secrets import Secrets
from app.repositories.base import BaseRepository


class SecretsRepository(BaseRepository[Secrets]):
    model = Secrets

    async def get_by_user_id(self, user_id: UUID) -> Secrets | None:
        """Находит Secrets по идентификатору пользователя.

        Args:
            user_id (UUID): идентификатор пользователя.

        Returns:
            Secrets | None: найденная запись секретов, либо None, если её нет.
        """
        result = await self.session.execute(select(Secrets).where(Secrets.user_id == user_id))
        return result.scalar_one_or_none()
