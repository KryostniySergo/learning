from sqlalchemy import select

from app.models.outbox_message import OutboxMessage, OutMessageStatus
from app.repositories.base import BaseRepository


class OutboxRepository(BaseRepository[OutboxMessage]):
    model = OutboxMessage

    async def get_pending(self, limit: int) -> list[OutboxMessage]:
        """Возвращает неотправленные сообщения в порядке создания.

        Args:
            limit (int): максимальное количество сообщений в одной пачке.

        Returns:
            list[OutboxMessage]: сообщения со статусом CREATED, отсортированные
                по occurred_at (старые — первыми), чтобы публиковать по порядку.
        """
        stmt = (
            select(OutboxMessage)
            .where(OutboxMessage.status == OutMessageStatus.CREATED)
            .order_by(OutboxMessage.occurred_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
