import asyncio
import logging

from app.adapters.kafka_producer import KafkaProducerAdapter
from app.core.config import settings
from app.models.outbox_message import OutboxMessageStatus
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)

BATCH_SIZE = 50
POLL_INTERVAL_SECONDS = 2


class OutboxPublisher:
    """Периодически публикует накопленные в outbox события в Kafka."""

    def __init__(self, producer: KafkaProducerAdapter) -> None:
        """Инициализирует публикатор.

        Args:
            producer (KafkaProducerAdapter): адаптер продюсера Kafka.
        """
        self._producer = producer
        self._running = False

    async def run_forever(self) -> None:
        """Бесконечно опрашивает outbox и публикует накопившиеся события."""
        self._running = True
        logger.info("OutboxPublisher started, polling every %s seconds", POLL_INTERVAL_SECONDS)

        while self._running:
            await self._publish_pending_batch()
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    def stop(self) -> None:
        """Помечает публикатор для остановки после текущей итерации."""
        self._running = False

    async def _publish_pending_batch(self) -> None:
        """Забирает пачку неотправленных событий и публикует их по одному."""
        async with UnitOfWork() as uow:
            messages = await uow.outbox.get_pending(BATCH_SIZE)
            message_ids = [message.id for message in messages]

        for message_id in message_ids:
            await self._publish_one(message_id)

    async def _publish_one(self, message_id) -> None:
        """Публикует одно событие в отдельной транзакции.

        Args:
            message_id (UUID): идентификатор строки outbox.
        """
        async with UnitOfWork() as uow:
            message = await uow.outbox.get_by_id(message_id)
            if message is None or message.status != OutboxMessageStatus.CREATED:
                return

            try:
                await self._producer.send(
                    topic=settings.kafka_topic,
                    key=message.aggregate_id,
                    value=message.payload,
                )
            except Exception:
                message.status = OutboxMessageStatus.FAILED
                message.retry_count += 1
                await uow.commit()
                logger.exception("Failed to publish outbox message %s", message_id)
                return

            message.status = OutboxMessageStatus.SENT
            await uow.commit()
            logger.info(
                "Published outbox message %s (event_type=%s)", message_id, message.event_type
            )
