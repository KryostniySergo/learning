from uuid import UUID

from sqlalchemy import select

from app.models.member import Member
from app.repositories.base import BaseRepository


class MemberRepository(BaseRepository[Member]):
    model = Member

    async def get_by_user_id(self, user_id: UUID) -> Member | None:
        """Находит самое раннее действующее членство пользователя.

        Используется при логине без явного указания компании — пользователь
        попадает в ту компанию, где состоит дольше всего.

        Args:
            user_id (UUID): идентификатор пользователя.

        Returns:
            Member | None: найденное членство, либо None.
        """
        result = await self.session.execute(
            select(Member)
            .where(Member.user_id == user_id)
            .where(Member.deleted_at.is_(None))
            .order_by(Member.created_at)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_company(self, user_id: UUID, company_id: UUID) -> Member | None:
        """Находит действующее членство пользователя в конкретной компании.

        Args:
            user_id (UUID): идентификатор пользователя.
            company_id (UUID): идентификатор компании.

        Returns:
            Member | None: найденное членство, либо None.
        """
        result = await self.session.execute(
            select(Member)
            .where(Member.user_id == user_id)
            .where(Member.company_id == company_id)
            .where(Member.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: UUID) -> list[Member]:
        """Находит все действующие членства пользователя.

        Args:
            user_id (UUID): идентификатор пользователя.

        Returns:
            list[Member]: членства пользователя, от самого раннего к позднему.
        """
        result = await self.session.execute(
            select(Member)
            .where(Member.user_id == user_id)
            .where(Member.deleted_at.is_(None))
            .order_by(Member.created_at)
        )
        return list(result.scalars().all())
