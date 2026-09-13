import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.adapters.kafka_producer import KafkaProducerAdapter
from app.core.config import settings
from app.models.outbox_message import OutboxMessage, OutboxMessageStatus
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
            await self._release_stale()
            await self._publish_pending_batch()
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    async def _release_stale(self) -> None:
        """Возвращает в очередь события, брошенные упавшим publisher'ом."""
        async with UnitOfWork() as uow:
            released = await uow.outbox.release_stale_processing()
        if released:
            logger.warning("released %d stale PROCESSING messages", released)

    def stop(self) -> None:
        """Помечает публикатор для остановки после текущей итерации."""
        self._running = False

    async def _publish_pending_batch(self) -> None:
        """Захватывает пачку событий и публикует их по одному."""
        async with UnitOfWork() as uow:
            messages = await uow.outbox.claim_pending(BATCH_SIZE)
            message_ids = [message.id for message in messages]

        for message_id in message_ids:
            await self._publish_one(message_id)

    async def _publish_one(self, message_id: UUID) -> None:
        """Публикует одно событие в отдельной транзакции.

        При ошибке планирует следующую попытку с экспоненциально растущей
        задержкой. После исчерпания лимита отправляет событие в DLQ-топик
        и помечает его как DEAD, чтобы оно больше не подбиралось.

        Args:
            message_id (UUID): идентификатор строки outbox.
        """
        async with UnitOfWork() as uow:
            message = await uow.outbox.get_by_id(message_id)
            if message is None or message.status != OutboxMessageStatus.PROCESSING:
                return

            try:
                await self._producer.send(
                    topic=message.topic,
                    key=message.aggregate_id,
                    value=message.payload,
                )
            except Exception:
                message.retry_count += 1

                if message.retry_count >= settings.outbox_max_retries:
                    await self._move_to_dlq(message)
                else:
                    delay = settings.outbox_retry_base_seconds * (2 ** (message.retry_count - 1))
                    message.status = OutboxMessageStatus.FAILED
                    message.next_retry_at = datetime.now(UTC) + timedelta(seconds=delay)
                    logger.warning(
                        "Publish failed for %s, retry %d/%d in %ds",
                        message_id,
                        message.retry_count,
                        settings.outbox_max_retries,
                        delay,
                    )

                await uow.commit()
                return

            message.status = OutboxMessageStatus.SENT
            message.next_retry_at = None
            await uow.commit()
            logger.info(
                "Published outbox message %s (event_type=%s, topic=%s)",
                message_id,
                message.event_type,
                message.topic,
            )

    async def _move_to_dlq(self, message: OutboxMessage) -> None:
        """Отправляет событие в DLQ после исчерпания попыток.

        Если и публикация в DLQ не удалась, событие всё равно помечается DEAD —
        оно остаётся в таблице outbox для ручного разбора.

        Args:
            message (OutboxMessage): событие, исчерпавшее попытки.
        """
        message.status = OutboxMessageStatus.DEAD
        message.next_retry_at = None

        try:
            await self._producer.send(
                topic=settings.kafka_dlq_topic,
                key=message.aggregate_id,
                value={
                    "original_topic": message.topic,
                    "retry_count": message.retry_count,
                    "envelope": message.payload,
                },
            )
            logger.error(
                "Outbox message %s moved to DLQ after %d attempts",
                message.id,
                message.retry_count,
            )
        except Exception:
            logger.exception("Outbox message %s marked DEAD, but DLQ publish also failed", message.id)
