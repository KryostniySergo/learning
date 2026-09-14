from datetime import UTC, datetime

from sqlalchemy import select

from app.models.idempotency_key import IdempotencyKey
from app.repositories.base import BaseRepository


class IdempotencyKeyRepository(BaseRepository[IdempotencyKey]):
    """Репозиторий для работы с ключами идемпотентности."""

    model = IdempotencyKey

    async def get_active(self, key: str) -> IdempotencyKey | None:
        """Находит непросроченную запись по ключу идемпотентности.

        Args:
            key (str): значение заголовка Idempotency-Key.

        Returns:
            IdempotencyKey | None: сохранённый результат, либо None.
        """
        result = await self.session.execute(
            select(IdempotencyKey).where(IdempotencyKey.key == key).where(IdempotencyKey.expires_at > datetime.now(UTC))
        )
        return result.scalar_one_or_none()
