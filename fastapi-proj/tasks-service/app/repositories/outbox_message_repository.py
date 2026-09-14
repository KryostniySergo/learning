from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select, update

from app.core.config import settings
from app.models.outbox_message import OutboxMessage, OutboxMessageStatus
from app.repositories.base import BaseRepository


class OutboxMessageRepository(BaseRepository[OutboxMessage]):
    """Репозиторий для работы с outbox сообщениями."""

    model = OutboxMessage

    async def claim_pending(self, limit: int) -> list[OutboxMessage]:
        """Атомарно захватывает пачку событий для публикации.

        Переводит выбранные строки в статус PROCESSING одним запросом и сразу
        возвращает их. Параллельно работающий publisher не увидит захваченные
        строки, поэтому одно событие не будет опубликовано дважды.

        Args:
            limit (int): максимальный размер пачки.

        Returns:
            list[OutboxMessage]: захваченные события в порядке возникновения.
        """
        now = datetime.now(UTC)

        candidates = (
            select(OutboxMessage.id)
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
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )

        result = await self.session.execute(
            update(OutboxMessage)
            .where(OutboxMessage.id.in_(candidates))
            .values(status=OutboxMessageStatus.PROCESSING)
            .returning(OutboxMessage)
        )
        await self.session.commit()

        return list(result.scalars().all())

    async def release_stale_processing(self, stale_after_seconds: int = 300) -> int:
        """Возвращает в очередь события, зависшие в статусе PROCESSING.

        Publisher мог упасть между захватом пачки и отправкой — тогда события
        остались бы в PROCESSING навсегда. Считаем захват просроченным, если
        он старше указанного времени.

        Args:
            stale_after_seconds (int): через сколько секунд захват считается брошенным.

        Returns:
            int: количество возвращённых в очередь событий.
        """
        threshold = datetime.now(UTC) - timedelta(seconds=stale_after_seconds)

        result = await self.session.execute(
            update(OutboxMessage)
            .where(OutboxMessage.status == OutboxMessageStatus.PROCESSING)
            .where(OutboxMessage.occurred_at < threshold)
            .values(status=OutboxMessageStatus.CREATED)
        )
        await self.session.commit()
        return result.rowcount
