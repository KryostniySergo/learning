import json
import logging
from collections.abc import AsyncIterator

from aiokafka import AIOKafkaConsumer

logger = logging.getLogger(__name__)


class KafkaConsumerAdapter:
    """Тонкая обёртка над aiokafka.AIOKafkaConsumer."""

    def __init__(self, bootstrap_servers: str, topic: str, group_id: str) -> None:
        """Инициализирует адаптер.

        Args:
            bootstrap_servers (str): адрес(а) Kafka-брокера.
            topic (str): топик, который нужно слушать.
            group_id (str): имя consumer group для этого сервиса.
        """
        self._consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )

    async def start(self) -> None:
        """Запускает соединение с Kafka."""
        await self._consumer.start()
        logger.info("KafkaConsumerAdapter started")

    async def stop(self) -> None:
        """Останавливает соединение с Kafka."""
        await self._consumer.stop()
        logger.info("KafkaConsumerAdapter stopped")

    async def consume(self) -> AsyncIterator[dict]:
        """Перебирает сообщения из топика, возвращая распарсенный envelope.

        Yields:
            dict: envelope события, распарсенный из JSON.
        """
        async for record in self._consumer:
            yield json.loads(record.value.decode("utf-8"))

    async def commit(self) -> None:
        """Коммитит offset текущей позиции чтения."""
        await self._consumer.commit()
