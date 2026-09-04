import asyncio
import logging
import signal

from app.adapters.kafka_consumer import KafkaConsumerAdapter
from app.core.config import settings
from app.core.logging import setup_logging
from app.services.inbox_service import InboxService
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


class InboxConsumer:
    """Читает события из Kafka и передаёт их в InboxService."""

    def __init__(self, consumer: KafkaConsumerAdapter) -> None:
        """Инициализирует консьюмер.

        Args:
            consumer (KafkaConsumerAdapter): адаптер, подключённый к нужному топику.
        """
        self._consumer = consumer
        self._running = False

    async def run_forever(self) -> None:
        """Читает и обрабатывает события, коммитя offset после каждого успеха."""
        self._running = True
        async for envelope in self._consumer.consume():
            if not self._running:
                break

            try:
                async with UnitOfWork() as uow:
                    await InboxService(uow).handle_event(envelope)
            except Exception:
                logger.exception("InboxConsumer: failed to process envelope, will retry")
                continue

            await self._consumer.commit()

    def stop(self) -> None:
        """Помечает консьюмер для остановки после текущей итерации."""
        self._running = False


async def main() -> None:
    """Точка входа процесса Inbox-консьюмера."""
    setup_logging()

    consumer = KafkaConsumerAdapter(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topic=settings.kafka_consumer_topic,
        group_id=settings.kafka_consumer_group,
    )
    await consumer.start()

    inbox_consumer = InboxConsumer(consumer)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, inbox_consumer.stop)

    try:
        await inbox_consumer.run_forever()
    finally:
        await consumer.stop()
        logger.info("InboxConsumer process stopped")


if __name__ == "__main__":
    asyncio.run(main())
