import asyncio
import logging
import signal

from app.adapters.kafka_consumer import KafkaConsumerAdapter
from app.core.config import settings
from app.core.event_types import EventType
from app.core.logging import setup_logging
from app.saga.command_handlers import AuthCommandHandler
from app.saga.onboarding_saga import OnboardingSaga
from app.schemas.event_envelope import EventEnvelope
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)

SAGA_START_EVENTS = {EventType.EMPLOYEE_REGISTERED.value}

SAGA_REPLY_EVENTS = {
    EventType.ORG_EMPLOYEE_ASSIGNED.value,
    EventType.ORG_EMPLOYEE_ASSIGNMENT_FAILED.value,
    EventType.TASKS_WELCOME_TASK_CREATED.value,
    EventType.TASKS_WELCOME_TASK_FAILED.value,
    EventType.ORG_EMPLOYEE_UNASSIGNED.value,
    EventType.AUTH_INVITE_INVALIDATED.value,
}

AUTH_COMMANDS = {EventType.AUTH_INVALIDATE_INVITE.value}


class SagaConsumer:
    """Читает стартовые события, ответы исполнителей и команды для auth-service."""

    def __init__(self, consumer: KafkaConsumerAdapter) -> None:
        """Инициализирует консьюмер.

        Args:
            consumer (KafkaConsumerAdapter): адаптер, подписанный на нужные топики.
        """
        self._consumer = consumer
        self._running = False

    async def run_forever(self) -> None:
        """Читает сообщения и направляет их в оркестратор или обработчик команд."""
        self._running = True
        async for raw_envelope in self._consumer.consume():
            if not self._running:
                break

            try:
                await self._dispatch(raw_envelope)
            except Exception:
                logger.exception("SagaConsumer: failed to process envelope, will retry")
                continue

            await self._consumer.commit()

    def stop(self) -> None:
        """Помечает консьюмер для остановки после текущей итерации."""
        self._running = False

    async def _dispatch(self, raw_envelope: dict) -> None:
        """Разбирает envelope и вызывает подходящий обработчик.

        Args:
            raw_envelope (dict): сырой envelope из Kafka.
        """
        envelope = EventEnvelope(**raw_envelope)
        event_type = envelope.event_type

        if event_type in SAGA_START_EVENTS:
            async with UnitOfWork() as uow:
                await OnboardingSaga(uow).start(envelope.payload)
            return

        if event_type in SAGA_REPLY_EVENTS:
            async with UnitOfWork() as uow:
                await OnboardingSaga(uow).handle_reply(event_type, envelope.payload)
            return

        if event_type in AUTH_COMMANDS:
            async with UnitOfWork() as uow:
                await AuthCommandHandler(uow).handle(event_type, envelope.payload)
            return

        logger.debug("saga consumer: ignoring event %s", event_type)


async def main() -> None:
    """Точка входа процесса саги."""
    setup_logging()

    consumer = KafkaConsumerAdapter(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topics=[
            settings.kafka_topic,
            settings.kafka_saga_commands_topic,
            settings.kafka_saga_replies_topic,
        ],
        group_id="saga-orchestrator",
    )
    await consumer.start()

    saga_consumer = SagaConsumer(consumer)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, saga_consumer.stop)

    try:
        await saga_consumer.run_forever()
    finally:
        await consumer.stop()
        logger.info("SagaConsumer process stopped")


if __name__ == "__main__":
    asyncio.run(main())
