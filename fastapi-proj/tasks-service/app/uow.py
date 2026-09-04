import logging
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.repositories.company_repository import CompanyRepository
from app.repositories.inbox_message_repository import InboxMessageRepository
from app.repositories.outbox_message_repository import OutboxMessageRepository
from app.repositories.task_assignee_repository import TaskAssigneeRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.task_watcher_repository import TaskWatcherRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UnitOfWork:
    """Единая граница транзакции на один запрос."""

    session: AsyncSession

    async def __aenter__(self) -> Self:
        """Открывает сессию БД и инициализирует все репозитории на этой сессии.

        Returns:
            Self: сам объект, готовый к использованию внутри блока `async with`.
        """
        self.session = async_session_maker()

        self.company = CompanyRepository(self.session)
        self.user = UserRepository(self.session)
        self.task = TaskRepository(self.session)
        self.task_watcher = TaskWatcherRepository(self.session)
        self.task_assignee = TaskAssigneeRepository(self.session)
        self.inbox = InboxMessageRepository(self.session)
        self.outbox = OutboxMessageRepository(self.session)

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Откатывает транзакцию при исключении и закрывает сессию в любом случае.

        Args:
            exc_type (type[BaseException] | None): тип исключения, если оно возникло.
            exc_val (BaseException | None): само исключение, если оно возникло.
            exc_tb (TracebackType | None): traceback исключения, если оно возникло.
        """
        if exc_type is not None:
            logger.warning("UoW rollback due to %s: %s", exc_type.__name__, exc_val)
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
