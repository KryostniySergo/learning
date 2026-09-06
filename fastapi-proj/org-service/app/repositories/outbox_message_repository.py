from sqlalchemy import select

from app.models.outbox_message import OutboxMessage, OutboxMessageStatus
from app.repositories.base import BaseRepository


class OutboxMessageRepository(BaseRepository[OutboxMessage]):
    model = OutboxMessage

    async def get_pending(self, limit: int) -> list[OutboxMessage]:
        """Находит неотправленные события в порядке их возникновения.

        Args:
            limit (int): максимальный размер пачки.

        Returns:
            list[OutboxMessage]: события со статусом CREATED.
        """
        result = await self.session.execute(
            select(OutboxMessage)
            .where(OutboxMessage.status == OutboxMessageStatus.CREATED)
            .order_by(OutboxMessage.occurred_at)
            .limit(limit)
        )
        return list(result.scalars().all())
