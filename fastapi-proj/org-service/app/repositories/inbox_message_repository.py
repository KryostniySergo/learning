from app.models.inbox_message import InboxMessage
from app.repositories.base import BaseRepository


class InboxMessageRepository(BaseRepository[InboxMessage]):
    model = InboxMessage