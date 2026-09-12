import logging
import secrets as secrets_lib
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.event_types import EventType
from app.core.exceptions import (
    EmailAlreadyTakenError,
    InviteExpiredError,
    InviteInvalidStatusError,
    InviteNotFoundError,
    ProfileNotFoundError,
)
from app.core.outbox import build_outbox_message
from app.models.account import Account
from app.models.invite import Invite, InviteStatus
from app.models.user import User
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


class ProfileService:
    """Управление личными данными сотрудника: имя и привязанная почта."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Инициализирует сервис.

        Args:
            uow (UnitOfWork): единица работы, дающая доступ к репозиториям и транзакции.
        """
        self.uow = uow

    async def get_profile(self, user_id: UUID) -> tuple[User, str]:
        """Возвращает личные данные пользователя вместе с текущей почтой.

        Args:
            user_id (UUID): идентификатор пользователя.

        Returns:
            tuple[User, str]: пользователь и его действующий адрес почты.

        Raises:
            ProfileNotFoundError: если пользователь или его почта не найдены.
        """
        user = await self.uow.users.get_by_id(user_id)
        if user is None:
            raise ProfileNotFoundError

        secrets_obj = await self.uow.secrets.get_by_user_id(user_id)
        if secrets_obj is None:
            raise ProfileNotFoundError

        account = await self.uow.accounts.get_by_id(secrets_obj.account_id)
        if account is None:
            raise ProfileNotFoundError

        return user, account.email

    async def update_name(self, user_id: UUID, first_name: str | None, last_name: str | None) -> User:
        """Меняет имя и фамилию пользователя.

        Публикует employee.updated, чтобы реплики в других сервисах не устарели.

        Args:
            user_id (UUID): идентификатор пользователя.
            first_name (str | None): новое имя, либо None если менять не нужно.
            last_name (str | None): новая фамилия, либо None если менять не нужно.

        Returns:
            User: обновлённый пользователь.

        Raises:
            ProfileNotFoundError: если пользователь не найден.
        """
        user = await self.uow.users.get_by_id(user_id)
        if user is None:
            raise ProfileNotFoundError

        if first_name is not None:
            user.name = first_name
        if last_name is not None:
            user.surname = last_name

        self.uow.outbox.add(
            build_outbox_message(
                event_type=EventType.EMPLOYEE_UPDATED,
                aggregate_id=user.id,
                payload={
                    "employee_id": str(user.id),
                    "name": user.name,
                    "surname": user.surname,
                },
            )
        )

        await self.uow.commit()
        logger.info("profile updated for user %s", user_id)
        return user

    async def request_email_change(self, user_id: UUID, new_email: str) -> str:
        """Начинает смену почты: создаёт аккаунт для нового адреса и инвайт.

        Сама привязка происходит только после подтверждения владения адресом.

        Args:
            user_id (UUID): идентификатор пользователя.
            new_email (str): новый адрес почты.

        Returns:
            str: токен подтверждения, отправляемый на новый адрес.

        Raises:
            ProfileNotFoundError: если пользователь не найден.
            EmailAlreadyTakenError: если адрес уже занят.
        """
        user = await self.uow.users.get_by_id(user_id)
        if user is None:
            raise ProfileNotFoundError

        existing = await self.uow.accounts.get_by_email(new_email)
        if existing is not None:
            logger.info("email change rejected: %s already taken", new_email)
            raise EmailAlreadyTakenError

        account = Account(id=uuid4(), email=new_email)
        self.uow.accounts.add(account)

        token = secrets_lib.token_urlsafe(32)
        self.uow.invites.add(
            Invite(
                id=uuid4(),
                token=token,
                account_id=account.id,
                user_id=user_id,
            )
        )

        await self.uow.commit()
        logger.info("email change requested for user %s to %s", user_id, new_email)
        return token

    async def confirm_email_change(self, user_id: UUID, invite_token: str) -> str:
        """Завершает смену почты, переключая учётные данные на новый адрес.

        Старый аккаунт помечается удалённым — адрес освобождается и может быть
        зарегистрирован заново.

        Args:
            user_id (UUID): идентификатор пользователя.
            invite_token (str): токен из письма на новый адрес.

        Returns:
            str: новый адрес почты.

        Raises:
            InviteNotFoundError: если инвайт не найден или выдан другому пользователю.
            InviteExpiredError: если срок действия инвайта истёк.
            InviteInvalidStatusError: если инвайт уже использован.
            ProfileNotFoundError: если учётные данные пользователя не найдены.
        """
        invite = await self.uow.invites.get_by_token(invite_token)
        if invite is None or invite.user_id != user_id:
            logger.warning("email confirm: invite not found for user %s", user_id)
            raise InviteNotFoundError

        if invite.expires_at < datetime.now(UTC):
            invite.status = InviteStatus.FAILED
            await self.uow.commit()
            raise InviteExpiredError

        if invite.status != InviteStatus.CREATED:
            raise InviteInvalidStatusError

        secrets_obj = await self.uow.secrets.get_by_user_id(user_id)
        if secrets_obj is None:
            raise ProfileNotFoundError

        old_account = await self.uow.accounts.get_by_id(secrets_obj.account_id)
        new_account = await self.uow.accounts.get_by_id(invite.account_id)
        if new_account is None:
            raise ProfileNotFoundError

        if old_account is not None:
            old_account.deleted_at = datetime.now(UTC)

        secrets_obj.account_id = new_account.id
        invite.status = InviteStatus.COMPLETED

        await self.uow.commit()
        logger.info("email changed for user %s to %s", user_id, new_account.email)
        return new_account.email
