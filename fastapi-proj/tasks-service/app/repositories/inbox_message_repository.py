from uuid import UUID

from sqlalchemy import select

from app.models.inbox_message import InboxMessage
from app.repositories.base import BaseRepository


class InboxMessageRepository(BaseRepository[InboxMessage]):
    model = InboxMessage

    async def get_by_event_id(self, event_id: UUID) -> InboxMessage | None:
        """Находит запись Inbox по event_id для проверки идемпотентности.

        Args:
            event_id (UUID): идентификатор события из envelope.

        Returns:
            InboxMessage | None: найденная запись, либо None.
        """
        result = await self.session.execute(
            select(InboxMessage).where(InboxMessage.event_id == event_id)
        )
        return result.scalar_one_or_none()
