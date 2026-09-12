from datetime import UTC, datetime

from sqlalchemy import or_, select

from app.core.config import settings
from app.models.outbox_message import OutboxMessage, OutboxMessageStatus
from app.repositories.base import BaseRepository


class OutboxMessageRepository(BaseRepository[OutboxMessage]):
    model = OutboxMessage

    async def get_pending(self, limit: int) -> list[OutboxMessage]:
        """Находит события, готовые к публикации.

        Забирает как новые события, так и ранее неудачные, у которых наступило
        время следующей попытки и не исчерпан лимит ретраев.

        Args:
            limit (int): максимальный размер пачки.

        Returns:
            list[OutboxMessage]: события в порядке возникновения.
        """
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(OutboxMessage)
            .where(
                or_(
                    OutboxMessage.status == OutboxMessageStatus.CREATED,
                    (OutboxMessage.status == OutboxMessageStatus.FAILED)
                    & (OutboxMessage.retry_count < settings.outbox_max_retries)
                    & (OutboxMessage.next_retry_at <= now),
                )
            )
            .order_by(OutboxMessage.occurred_at)
            .limit(limit)
        )
        return list(result.scalars().all())
