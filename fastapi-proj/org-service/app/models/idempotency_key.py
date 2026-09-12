from datetime import UTC, datetime, timedelta
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import INT, TIMESTAMP, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def default_expiry() -> datetime:
    """Возвращает срок хранения записи об идемпотентном запросе.

    Returns:
        datetime: момент, после которого ключ можно переиспользовать.
    """
    return datetime.now(UTC) + timedelta(hours=24)


class IdempotencyKey(Base):
    """Сохранённый результат небезопасной операции.

    Позволяет вернуть тот же ответ при повторном запросе с тем же ключом —
    например, если клиент не дождался ответа из-за обрыва связи и повторил запрос.
    """

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    method: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(String(255))

    status_code: Mapped[int] = mapped_column(INT)
    response_body: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=default_expiry)
