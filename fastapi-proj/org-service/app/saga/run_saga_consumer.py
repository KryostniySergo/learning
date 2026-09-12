import asyncio
import logging
import signal

from app.adapters.kafka_consumer import KafkaConsumerAdapter
from app.core.config import settings
from app.core.logging import setup_logging
from app.saga.command_handlers import EmployeeNotReplicatedError, OrgCommandHandler
from app.schemas.event_envelope import EventEnvelope
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


class SagaCommandConsumer:
    """Слушает топик команд саги и исполняет адресованные org-service."""

    def __init__(self, consumer: KafkaConsumerAdapter) -> None:
        """Инициализирует консьюмер.

        Args:
            consumer (KafkaConsumerAdapter): адаптер, подписанный на топик команд.
        """
        self._consumer = consumer
        self._running = False

    async def run_forever(self) -> None:
        """Читает команды и передаёт их обработчику.

        Если обработчик поднял исключение, offset не коммитится — Kafka
        передоставит команду позже. Так решается гонка с репликацией.
        """
        self._running = True
        async for raw_envelope in self._consumer.consume():
            if not self._running:
                break

            try:
                envelope = EventEnvelope(**raw_envelope)
                async with UnitOfWork() as uow:
                    await OrgCommandHandler(uow).handle(envelope.event_type, envelope.payload)
            except EmployeeNotReplicatedError:
                logger.info("command waiting for replica, will retry")
                await self._consumer.seek_to_committed()
                await asyncio.sleep(2)
                continue
            except Exception:
                logger.exception("SagaCommandConsumer: command not processed, will retry")
                await self._consumer.seek_to_committed()
                await asyncio.sleep(2)
                continue

            await self._consumer.commit()

    def stop(self) -> None:
        """Помечает консьюмер для остановки после текущей итерации."""
        self._running = False


async def main() -> None:
    """Точка входа процесса обработчика команд саги."""
    setup_logging()

    consumer = KafkaConsumerAdapter(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topics=[settings.kafka_saga_commands_topic],
        group_id="org-saga-commands",
    )
    await consumer.start()

    saga_consumer = SagaCommandConsumer(consumer)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, saga_consumer.stop)

    try:
        await saga_consumer.run_forever()
    finally:
        await consumer.stop()
        logger.info("SagaCommandConsumer process stopped")


if __name__ == "__main__":
    asyncio.run(main())
