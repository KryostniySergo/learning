from sqlalchemy import select

from app.models.account import Account
from app.repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    """Репозиторий для работы с аккаунтами (почты)."""

    model = Account

    async def get_by_email(self, email: str) -> Account | None:
        """Находит действующий Account по email.

        Мягко удалённые аккаунты игнорируются: адрес считается свободным
        и может быть зарегистрирован заново.

        Args:
            email (str): почта для поиска.

        Returns:
            Account | None: найденный аккаунт, либо None.
        """
        result = await self.session.execute(
            select(Account).where(Account.email == email).where(Account.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()
