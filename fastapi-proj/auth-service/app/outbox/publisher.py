import asyncio
import logging

from app.adapters.kafka_producer import KafkaProducerAdapter
from app.core.config import settings
from app.models.outbox_message import OutMessageStatus
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)

BATCH_SIZE = 50
POLL_INTERVAL_SECONDS = 2


class OutboxPublisher:
    """Фоновый процесс, публикующий накопленные события outbox в Kafka."""

    def __init__(self, producer: KafkaProducerAdapter) -> None:
        """Инициализирует publisher.

        Args:
            producer (KafkaProducerAdapter): адаптер, скрывающий детали работы с Kafka.
        """
        self._producer = producer
        self._running = False

    async def run_forever(self) -> None:
        """Запускает бесконечный цикл опроса outbox до вызова stop()."""
        self._running = True
        logger.info("OutboxPublisher started, polling every %s seconds", POLL_INTERVAL_SECONDS)
        while self._running:
            await self._publish_pending_batch()
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    def stop(self) -> None:
        """Останавливает цикл после текущей итерации (graceful shutdown)."""
        self._running = False
        logger.info("OutboxPublisher stop requested")

    async def _publish_pending_batch(self) -> None:
        """Забирает одну пачку сообщений CREATED и пытается отправить каждое в Kafka.

        Каждое сообщение обрабатывается и коммитится отдельно: неудача одного
        сообщения не должна блокировать публикацию остальных в пачке.
        """
        async with UnitOfWork() as uow:
            messages = await uow.outbox.get_pending(BATCH_SIZE)

        for message in messages:
            async with UnitOfWork() as uow:
                db_message = await uow.outbox.get_by_id(message.id)
                if db_message is None or db_message.status != OutMessageStatus.CREATED:
                    continue

                try:
                    await self._producer.send(
                        topic=settings.kafka_topic,
                        key=str(db_message.aggregate_id),
                        value=db_message.payload,
                    )
                except Exception:
                    logger.exception(
                        "Failed to publish outbox message %s (event_type=%s)",
                        db_message.id,
                        db_message.event_type,
                    )
                    db_message.status = OutMessageStatus.FAILED
                    db_message.retry_count += 1
                else:
                    db_message.status = OutMessageStatus.SENT
                    logger.info(
                        "Published outbox message %s (event_type=%s)",
                        db_message.id,
                        db_message.event_type,
                    )

                await uow.commit()
