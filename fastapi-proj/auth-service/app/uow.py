import logging
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.repositories.account_repository import AccountRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.invite_repository import InviteRepository
from app.repositories.member_repository import MemberRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.secrets_repository import SecretsRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UnitOfWork:
    """Единая граница транзакции на один запрос.

    Открывает сессию при входе в контекст, коммитит при успешном выходе,
    откатывает при исключении. Репозитории создаются лениво, все на одной сессии.
    """

    session: AsyncSession

    async def __aenter__(self) -> Self:
        """Открывает сессию БД и инициализирует все репозитории на этой сессии.

        Returns:
            Self: сам объект, готовый к использованию внутри блока `async with`.
        """
        self.session = async_session_maker()

        self.accounts = AccountRepository(self.session)
        self.companies = CompanyRepository(self.session)
        self.users = UserRepository(self.session)
        self.members = MemberRepository(self.session)
        self.invites = InviteRepository(self.session)
        self.secrets = SecretsRepository(self.session)
        self.outbox = OutboxRepository(self.session)

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Откатывает транзакцию при исключении и закрывает сессию в любом случае.

        Args:
            exc_type (type[BaseException] | None): тип исключения, если оно возникло внутри блока.
            exc_val (BaseException | None): само исключение, если оно возникло.
            exc_tb (TracebackType | None): traceback исключения, если оно возникло.
        """
        if exc_type is not None:
            logger.warning(
                "UoW rollback due to %s: %s",
                exc_type.__name__,
                exc_val,
            )
            await self.session.rollback()
        await self.session.close()

    async def commit(self) -> None:
        """Коммитит текущую транзакцию."""
        await self.session.commit()
        logger.debug("UoW commit successful")

    async def rollback(self) -> None:
        """Откатывает текущую транзакцию вручную."""
        await self.session.rollback()
        logger.debug("UoW manual rollback")
