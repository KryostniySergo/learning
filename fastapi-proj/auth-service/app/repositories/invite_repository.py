from sqlalchemy import select

from app.models.invite import Invite
from app.repositories.base import BaseRepository


class InviteRepository(BaseRepository[Invite]):
    model = Invite

    async def get_by_token(self, token: str) -> Invite | None:
        """Находит Invite по токену.

        Args:
            token (str): токен инвайта, полученный по ссылке из письма.

        Returns:
            Invite | None: найденный инвайт, либо None, если токен не существует.
        """
        result = await self.session.execute(select(Invite).where(Invite.token == token))
        return result.scalar_one_or_none()
