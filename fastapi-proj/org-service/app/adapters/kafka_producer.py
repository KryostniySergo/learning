import json
import logging
from uuid import UUID

from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)


class KafkaProducerAdapter:
    """Тонкая обёртка над aiokafka.AIOKafkaProducer."""

    def __init__(self, bootstrap_servers: str) -> None:
        """Инициализирует адаптер.

        Args:
            bootstrap_servers (str): адрес(а) Kafka-брокера.
        """
        self._producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)

    async def start(self) -> None:
        """Запускает соединение с Kafka."""
        await self._producer.start()
        logger.info("KafkaProducerAdapter started")

    async def stop(self) -> None:
        """Останавливает соединение с Kafka."""
        await self._producer.stop()
        logger.info("KafkaProducerAdapter stopped")

    async def send(self, topic: str, key: UUID, value: dict) -> None:
        """Публикует сообщение в топик, дожидаясь подтверждения от брокера.

        Args:
            topic (str): целевой топик.
            key (UUID): ключ партиционирования — aggregate_id события.
            value (dict): envelope события.
        """
        await self._producer.send_and_wait(
            topic,
            key=str(key).encode("utf-8"),
            value=json.dumps(value).encode("utf-8"),
        )
