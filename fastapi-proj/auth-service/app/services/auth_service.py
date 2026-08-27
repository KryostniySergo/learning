import logging
import secrets as secrets_lib
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.models.account import Account
from app.models.invite import Invite
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


class AccountAlreadyExistsError(Exception):
    """Исключение при попытке создать Account с уже занятой почтой (гонка запросов)."""


class AuthService:
    """Бизнес-логика аутентификации: регистрация, инвайты, вход."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Инициализирует сервис.

        Args:
            uow (UnitOfWork): единица работы, дающая доступ к репозиториям и транзакции.
        """
        self.uow = uow

    async def check_account(self, email: str) -> bool:
        """Проверяет, свободна ли почта, и если да — создаёт Account и Invite.

        Args:
            email (str): почта, которую нужно проверить и зарегистрировать.

        Returns:
            bool: True, если почта была свободна и инвайт создан, False — если почта уже занята.

        Raises:
            AccountAlreadyExistsError: если почта оказалась занята в момент commit
                (гонка запросов, не отловленная предварительной проверкой).
        """
        existing = await self.uow.accounts.get_by_email(email)
        if existing is not None:
            logger.info("check_account: %s already taken", email)
            return False

        account = Account(id=uuid4(), email=email)
        self.uow.accounts.add(account)

        invite = Invite(
            token=secrets_lib.token_urlsafe(32),
            account_id=account.id,
        )
        self.uow.invites.add(invite)

        try:
            await self.uow.commit()
        except IntegrityError as exc:
            # почта была занята параллельным запросом между SELECT и INSERT
            await self.uow.rollback()
            logger.warning("check_account: race condition on %s", email)
            raise AccountAlreadyExistsError from exc

        logger.info("check_account: invite created for %s (account_id=%s)", email, account.id)
        # "отправка" кода
        logger.debug("[MAIL MOCK] Invite token for %s: %s", email, invite.token)

        return True
