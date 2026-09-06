from uuid import UUID

from pydantic import BaseModel


class EventEnvelope(BaseModel):
    """Структура envelope события, приходящего из Kafka."""

    event_id: UUID
    event_type: str
    schema_version: int
    producer: str
    payload: dict
