import json
import logging
from collections.abc import AsyncIterator

from aiokafka import AIOKafkaConsumer

logger = logging.getLogger(__name__)


class KafkaConsumerAdapter:
    """Тонкая обёртка над aiokafka.AIOKafkaConsumer.

    Поддерживает подписку на один или несколько топиков.
    """

    def __init__(self, bootstrap_servers: str, topics: list[str], group_id: str) -> None:
        """Инициализирует адаптер.

        Args:
            bootstrap_servers (str): адрес(а) Kafka-брокера.
            topics (list[str]): топики, на которые нужно подписаться.
            group_id (str): имя consumer group.
        """
        self._consumer = AIOKafkaConsumer(
            *topics,
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
        """Перебирает сообщения, возвращая распарсенный envelope.

        Yields:
            dict: envelope события, распарсенный из JSON.
        """
        async for record in self._consumer:
            yield json.loads(record.value.decode("utf-8"))

    async def commit(self) -> None:
        """Коммитит offset текущей позиции чтения."""
        await self._consumer.commit()

    async def seek_to_committed(self) -> None:
        """Возвращает позицию чтения к последнему закоммиченному offset.

        Нужно для повторной обработки сообщения внутри того же процесса:
        без этого aiokafka продолжит читать дальше, не возвращаясь назад,
        и незакоммиченное сообщение будет повторно доставлено только
        после перезапуска консьюмера.
        """
        for partition in self._consumer.assignment():
            committed = await self._consumer.committed(partition)
            if committed is not None:
                self._consumer.seek(partition, committed)
            else:
                await self._consumer.seek_to_beginning(partition)
