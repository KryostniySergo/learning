from uuid import UUID

from pydantic import BaseModel


class EventEnvelope(BaseModel):
    """Структура envelope события, приходящего из Kafka.

    Валидирует обязательные поля до того, как payload попадёт в бизнес-логику —
    если продюсер отправит событие с опечаткой в ключе или без обязательного
    поля, ошибка будет явной (ValidationError) уже на этапе парсинга.
    """

    event_id: UUID
    event_type: str
    schema_version: int
    producer: str
    payload: dict
