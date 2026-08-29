import json

from aiokafka import AIOKafkaProducer


class KafkaProducerAdapter:
    """Обёртка над aiokafka, прячущая детали работы с Kafka от остального кода."""

    def __init__(self, bootstrap_servers: str) -> None:
        """Инициализирует адаптер (без подключения к брокеру).

        Args:
            bootstrap_servers (str): адрес(а) брокеров Kafka, например 'localhost:9092'.
        """
        self._producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)

    async def start(self) -> None:
        """Устанавливает соединение с брокером. Вызывается один раз при старте процесса."""
        await self._producer.start()

    async def stop(self) -> None:
        """Закрывает соединение с брокером. Вызывается при graceful shutdown."""
        await self._producer.stop()

    async def send(self, topic: str, key: str, value: dict) -> None:
        """Публикует сообщение в топик и ждёт подтверждения доставки (ack).

        Args:
            topic (str): имя топика Kafka.
            key (str): ключ партиционирования (aggregate_id), гарантирует порядок
                событий одной сущности внутри партиции.
            value (dict): payload сообщения (envelope), будет сериализован в JSON.

        Raises:
            aiokafka.errors.KafkaError: при сбое отправки (потере соединения,
                таймауте и т.п.) — вызывающий код (publisher) должен это поймать
                и пометить сообщение как FAILED для повторной попытки.
        """
        await self._producer.send_and_wait(
            topic,
            key=key.encode("utf-8"),
            value=json.dumps(value).encode("utf-8"),
        )
