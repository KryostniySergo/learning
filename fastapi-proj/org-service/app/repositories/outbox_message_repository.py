from app.models.outbox_message import OutboxMessage
from app.repositories.base import BaseRepository


class OutboxMessageRepository(BaseRepository[OutboxMessage]):
    model = OutboxMessage