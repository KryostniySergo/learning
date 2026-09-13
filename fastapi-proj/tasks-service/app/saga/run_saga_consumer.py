import asyncio
import logging
import signal
from collections import defaultdict

from app.adapters.kafka_consumer import KafkaConsumerAdapter
from app.adapters.kafka_producer import KafkaProducerAdapter
from app.core.config import settings
from app.core.logging import setup_logging
from app.saga.command_handlers import EmployeeNotReplicatedError, TasksCommandHandler
from app.schemas.event_envelope import EventEnvelope
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)

MAX_WAIT_ATTEMPTS = 10
RETRY_DELAY_SECONDS = 2


class SagaCommandConsumer:
    """Слушает топик команд саги и исполняет адресованные сервису."""

    def __init__(self, consumer: KafkaConsumerAdapter, producer: KafkaProducerAdapter) -> None:
        """Инициализирует консьюмер.

        Args:
            consumer (KafkaConsumerAdapter): адаптер, подписанный на топик команд.
            producer (KafkaProducerAdapter): адаптер для отправки в DLQ.
        """
        self._consumer = consumer
        self._producer = producer
        self._running = False
        self._attempts: dict[str, int] = defaultdict(int)

    async def run_forever(self) -> None:
        """Читает команды и передаёт их обработчику.

        Команда, ожидающая появления реплики, перечитывается ограниченное число
        раз. После исчерпания лимита она уходит в DLQ, чтобы не блокировать
        обработку остальных команд в той же партиции.
        """
        self._running = True
        async for raw_envelope in self._consumer.consume():
            if not self._running:
                break

            event_id = str(raw_envelope.get("event_id", "unknown"))

            try:
                envelope = EventEnvelope(**raw_envelope)
                async with UnitOfWork() as uow:
                    await TasksCommandHandler(uow).handle(envelope.event_type, envelope.payload)
            except EmployeeNotReplicatedError:
                self._attempts[event_id] += 1

                if self._attempts[event_id] >= MAX_WAIT_ATTEMPTS:
                    logger.error(
                        "command %s gave up after %d attempts waiting for replica",
                        event_id,
                        self._attempts[event_id],
                    )
                    await self._send_to_dlq(raw_envelope, "replica never arrived")
                    del self._attempts[event_id]
                    await self._consumer.commit()
                    continue

                logger.info(
                    "command %s waiting for replica, attempt %d/%d",
                    event_id,
                    self._attempts[event_id],
                    MAX_WAIT_ATTEMPTS,
                )
                await self._consumer.seek_to_committed()
                await asyncio.sleep(RETRY_DELAY_SECONDS)
                continue
            except Exception:
                logger.exception("SagaCommandConsumer: command %s failed", event_id)
                await self._send_to_dlq(raw_envelope, "unhandled error")
                await self._consumer.commit()
                continue

            self._attempts.pop(event_id, None)
            await self._consumer.commit()

    def stop(self) -> None:
        """Помечает консьюмер для остановки после текущей итерации."""
        self._running = False

    async def _send_to_dlq(self, raw_envelope: dict, reason: str) -> None:
        """Отправляет необработанную команду в DLQ.

        Args:
            raw_envelope (dict): исходное сообщение.
            reason (str): причина отбраковки.
        """
        try:
            await self._producer.send(
                topic=settings.kafka_dlq_topic,
                key=raw_envelope.get("payload", {}).get("employee_id", "unknown"),
                value={
                    "reason": reason,
                    "consumer": settings.consumer_name,
                    "envelope": raw_envelope,
                },
            )
        except Exception:
            logger.exception("failed to send command to DLQ")


async def main() -> None:
    """Точка входа процесса обработчика команд саги."""
    setup_logging()

    consumer = KafkaConsumerAdapter(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topics=[settings.kafka_saga_commands_topic],
        group_id="tasks-saga-commands",
    )
    producer = KafkaProducerAdapter(bootstrap_servers=settings.kafka_bootstrap_servers)

    await consumer.start()
    await producer.start()

    saga_consumer = SagaCommandConsumer(consumer, producer)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, saga_consumer.stop)

    try:
        await saga_consumer.run_forever()
    finally:
        await consumer.stop()
        await producer.stop()
        logger.info("SagaCommandConsumer process stopped")


if __name__ == "__main__":
    asyncio.run(main())
