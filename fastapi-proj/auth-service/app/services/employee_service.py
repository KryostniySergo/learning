import logging
import secrets as secrets_lib
from datetime import datetime
from uuid import UUID, uuid4

from app.core.event_types import EventType
from app.core.exceptions import (
    EmployeeAlreadyInCompanyError,
    InviteExpiredError,
    InviteInvalidStatusError,
    InviteNotFoundError,
    NotAuthorizedError,
    UserNotFoundError,
)
from app.core.outbox import build_outbox_message
from app.core.security import hash_password
from app.models.account import Account
from app.models.invite import Invite, InviteStatus
from app.models.member import Member
from app.models.member import Role as MemberRole
from app.models.secrets import Secrets
from app.models.user import User
from app.schemas.current_user import CurrentUser
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


class EmployeeService:
    """Бизнес-логика создания сотрудников администратором и их регистрации."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Инициализирует сервис.

        Args:
            uow (UnitOfWork): единица работы, дающая доступ к репозиториям и транзакции.
        """
        self.uow: UnitOfWork = uow

    async def create_employee(
        self,
        email: str,
        first_name: str,
        last_name: str,
        current_user: CurrentUser,
    ) -> tuple[UUID, str | None]:
        """Создаёт сотрудника в компании администратора и генерирует инвайт.

        Поддерживает три случая: новая почта, почта уже зарегистрирована
        (переиспользуем User, добавляем членство во второй компании) и почта
        с незавершённой регистрацией (переиспользуем Account, выпускаем инвайт).

        Args:
            email (str): почта создаваемого сотрудника.
            first_name (str): имя сотрудника.
            last_name (str): фамилия сотрудника.
            current_user (CurrentUser): контекст администратора.

        Returns:
            tuple[UUID, str | None]: id сотрудника и токен инвайта. Токен равен None,
                если сотрудник уже зарегистрирован и пароль ему задавать не нужно.

        Raises:
            NotAuthorizedError: если пользователь не администратор компании.
            EmployeeAlreadyInCompanyError: если сотрудник уже состоит в этой компании.
        """
        if not current_user.is_admin:
            logger.warning("create_employee denied for user %s", current_user.user_id)
            raise NotAuthorizedError

        company_id: UUID = current_user.company_id
        account: Account | None = await self.uow.accounts.get_by_email(email)

        if account is None:
            return await self._create_new_employee(email, first_name, last_name, company_id)

        secrets_obj: Secrets | None = await self.uow.secrets.get_by_account_id(account.id)
        if secrets_obj is not None:
            return await self._attach_existing_user(secrets_obj.user_id, company_id), None

        return await self._reinvite_pending_account(account, first_name, last_name, company_id)

    async def register_employee(self, invite_token: str, password: str) -> UUID:
        """Завершает регистрацию сотрудника по инвайту, задавая пароль.

        Публикует employee.registered — стартовое событие саги онбординга.

        Args:
            invite_token (str): токен инвайта из письма.
            password (str): пароль в открытом виде.

        Returns:
            UUID: id зарегистрированного сотрудника.

        Raises:
            InviteNotFoundError: если инвайт не найден или не привязан к сотруднику.
            InviteExpiredError: если срок действия инвайта истёк.
            InviteInvalidStatusError: если инвайт уже использован или отменён.
        """
        invite: Invite | None = await self.uow.invites.get_by_token(invite_token)
        if invite is None or invite.user_id is None:
            logger.warning("register_employee: invite not found or has no user")
            raise InviteNotFoundError

        if invite.expires_at < datetime.now():
            invite.status = InviteStatus.FAILED
            await self.uow.commit()
            logger.info("register_employee: invite expired for user %s", invite.user_id)
            raise InviteExpiredError

        if invite.status != InviteStatus.CREATED:
            logger.warning("register_employee: invalid status %s", invite.status)
            raise InviteInvalidStatusError

        self.uow.secrets.add(
            Secrets(
                id=uuid4(),
                user_id=invite.user_id,
                account_id=invite.account_id,
                password_hash=hash_password(password),
            )
        )

        invite.status = InviteStatus.COMPLETED

        member = await self.uow.members.get_by_user_id(invite.user_id)
        self.uow.outbox.add(
            build_outbox_message(
                event_type=EventType.EMPLOYEE_REGISTERED,
                aggregate_id=invite.user_id,
                payload={
                    "employee_id": str(invite.user_id),
                    "company_id": str(member.company_id) if member else None,
                    "invite_id": str(invite.id),
                },
            )
        )

        await self.uow.commit()
        logger.info("register_employee: user %s registered", invite.user_id)
        return invite.user_id

    async def _create_new_employee(
        self, email: str, first_name: str, last_name: str, company_id: UUID
    ) -> tuple[UUID, str]:
        """Создаёт нового сотрудника с нуля: аккаунт, пользователя, членство, инвайт.

        Args:
            email (str): почта сотрудника.
            first_name (str): имя сотрудника.
            last_name (str): фамилия сотрудника.
            company_id (UUID): компания, в которую добавляется сотрудник.

        Returns:
            tuple[UUID, str]: id сотрудника и токен выпущенного инвайта.
        """
        account = Account(id=uuid4(), email=email)
        self.uow.accounts.add(account)

        user = User(id=uuid4(), name=first_name, surname=last_name)
        self.uow.users.add(user)
        await self.uow.session.flush()

        self.uow.members.add(
            Member(
                id=uuid4(),
                user_id=user.id,
                company_id=company_id,
                role=MemberRole.USER,
            )
        )

        token: str = secrets_lib.token_urlsafe(32)
        self.uow.invites.add(
            Invite(
                id=uuid4(),
                token=token,
                account_id=account.id,
                user_id=user.id,
            )
        )

        self._publish_employee_created(user, company_id)
        await self.uow.commit()

        logger.info("employee created: %s (%s) in company %s", user.id, email, company_id)
        logger.debug("[MAIL MOCK] Invite token for %s: %s", email, token)
        return user.id, token

    async def _attach_existing_user(self, user_id: UUID, company_id: UUID) -> UUID:
        """Добавляет уже зарегистрированного пользователя в ещё одну компанию.

        Args:
            user_id (UUID): id существующего пользователя.
            company_id (UUID): компания, в которую его добавляют.

        Returns:
            UUID: id сотрудника.

        Raises:
            EmployeeAlreadyInCompanyError: если он уже состоит в этой компании.
        """
        existing = await self.uow.members.get_by_user_and_company(user_id, company_id)
        if existing is not None:
            raise EmployeeAlreadyInCompanyError

        self.uow.members.add(
            Member(
                id=uuid4(),
                user_id=user_id,
                company_id=company_id,
                role=MemberRole.USER,
            )
        )

        user: User | None = await self.uow.users.get_by_id(user_id)
        if user is None:
            logger.error("user %s referenced by secrets but missing", user_id)
            raise UserNotFoundError

        self._publish_employee_created(user, company_id)
        await self.uow.commit()

        logger.info("existing user %s attached to company %s", user_id, company_id)
        return user_id

    async def _reinvite_pending_account(
        self, account: Account, first_name: str, last_name: str, company_id: UUID
    ) -> tuple[UUID, str]:
        """Обрабатывает почту с незавершённой регистрацией.

        Переиспользует существующий Account и, если он есть, ранее созданного
        пользователя. Выпускает новый инвайт, чтобы сотрудник задал пароль.

        Args:
            account (Account): существующий аккаунт с незавершённой регистрацией.
            first_name (str): имя сотрудника.
            last_name (str): фамилия сотрудника.
            company_id (UUID): компания, в которую добавляется сотрудник.

        Returns:
            tuple[UUID, str]: id сотрудника и токен нового инвайта.

        Raises:
            EmployeeAlreadyInCompanyError: если он уже состоит в этой компании.
        """
        user_id: UUID | None = await self.uow.invites.get_user_id_by_account(account.id)

        if user_id is None:
            user = User(id=uuid4(), name=first_name, surname=last_name)
            self.uow.users.add(user)
            await self.uow.session.flush()
            user_id = user.id
        else:
            user: User | None = await self.uow.users.get_by_id(user_id)
            if user is None:
                logger.error("user %s referenced by invite but missing", user_id)
                raise UserNotFoundError

            existing: Member | None = await self.uow.members.get_by_user_and_company(user_id, company_id)
            if existing is not None:
                raise EmployeeAlreadyInCompanyError

        self.uow.members.add(
            Member(
                id=uuid4(),
                user_id=user_id,
                company_id=company_id,
                role=MemberRole.USER,
            )
        )

        token: str = secrets_lib.token_urlsafe(32)
        self.uow.invites.add(
            Invite(
                id=uuid4(),
                token=token,
                account_id=account.id,
                user_id=user_id,
            )
        )

        self._publish_employee_created(user, company_id)
        await self.uow.commit()

        logger.info(
            "pending account %s reinvited as employee %s in company %s",
            account.email,
            user_id,
            company_id,
        )
        logger.debug("[MAIL MOCK] Invite token for %s: %s", account.email, token)
        return user_id, token

    def _publish_employee_created(self, user: User, company_id: UUID) -> None:
        """Кладёт событие employee.created в outbox.

        Args:
            user (User): созданный или переиспользованный пользователь.
            company_id (UUID): компания, в которой он теперь состоит.
        """
        self.uow.outbox.add(
            build_outbox_message(
                event_type=EventType.EMPLOYEE_CREATED,
                aggregate_id=user.id,
                payload={
                    "employee_id": str(user.id),
                    "name": user.name,
                    "surname": user.surname,
                    "company_id": str(company_id),
                },
            )
        )
