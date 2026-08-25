from sqlalchemy import select

from app.models.account import Account
from app.repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    model = Account

    async def get_by_email(self, email: str) -> Account | None:
        """Находит Account по email.

        Args:
            email (str): почта для поиска.

        Returns:
            Account | None: найденный аккаунт, либо None, если такой почты нет.
        """
        result = await self.session.execute(select(Account).where(Account.email == email))
        return result.scalar_one_or_none()
