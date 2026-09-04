from uuid import UUID

from sqlalchemy import select

from app.models.member import Member
from app.repositories.base import BaseRepository


class MemberRepository(BaseRepository[Member]):
    model = Member

    async def get_by_user_id(self, user_id: UUID) -> Member | None:
        """Находит действующее членство пользователя в компании.

        Args:
            user_id (UUID): идентификатор пользователя.

        Returns:
            Member | None: найденное членство, либо None.
        """
        result = await self.session.execute(
            select(Member).where(Member.user_id == user_id).where(Member.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()
