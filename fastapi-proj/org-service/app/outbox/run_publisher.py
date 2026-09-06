import asyncio
import logging
import signal

from app.adapters.kafka_producer import KafkaProducerAdapter
from app.core.config import settings
from app.core.logging import setup_logging
from app.outbox.publisher import OutboxPublisher

logger = logging.getLogger(__name__)


async def main() -> None:
    """Точка входа процесса Outbox-публикатора."""
    setup_logging()

    producer = KafkaProducerAdapter(bootstrap_servers=settings.kafka_bootstrap_servers)
    await producer.start()

    publisher = OutboxPublisher(producer)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, publisher.stop)

    try:
        await publisher.run_forever()
    finally:
        await producer.stop()
        logger.info("OutboxPublisher process stopped")


if __name__ == "__main__":
    asyncio.run(main())
