import json
from uuid import UUID

from aiokafka import AIOKafkaProducer


class KafkaProducerAdapter:
    """Обёртка над aiokafka, прячущая детали работы с Kafka от остального кода."""

    def __init__(self, bootstrap_servers: str) -> None:
        """Инициализирует адаптер (без подключения к брокеру).

        Args:
            bootstrap_servers (str): адрес(а) брокеров Kafka, например 'localhost:9092'.
        """
        self._producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            acks="all",
            enable_idempotence=True,
            request_timeout_ms=5000,
        )

    async def start(self) -> None:
        """Устанавливает соединение с брокером. Вызывается один раз при старте процесса."""
        await self._producer.start()

    async def stop(self) -> None:
        """Закрывает соединение с брокером. Вызывается при graceful shutdown."""
        await self._producer.stop()

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
