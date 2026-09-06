from datetime import datetime
from uuid import UUID, uuid4

from app.core.config import settings
from app.core.event_types import EventType
from app.models.outbox_message import OutboxMessage


def build_outbox_message(
    event_type: EventType,
    aggregate_id: UUID,
    payload: dict,
    topic: str | None = None,
) -> OutboxMessage:
    """Собирает готовый OutboxMessage с envelope вокруг payload.

    Args:
        event_type (EventType): тип события.
        aggregate_id (UUID): идентификатор сущности, к которой относится событие
            (используется как ключ партиционирования Kafka).
        payload (dict): полезная нагрузка события.
        topic (str | None): целевой топик Kafka. По умолчанию — доменный топик сервиса.

    Returns:
        OutboxMessage: объект, готовый к добавлению в сессию.
    """
    event_id = uuid4()

    envelope = {
        "event_id": str(event_id),
        "event_type": event_type.value,
        "schema_version": 1,
        "producer": settings.producer_name,
        "payload": payload,
    }

    return OutboxMessage(
        id=uuid4(),
        event_id=event_id,
        event_type=event_type.value,
        topic=topic or settings.kafka_topic,
        aggregate_id=aggregate_id,
        occurred_at=datetime.now(),
        payload=envelope,
    )
