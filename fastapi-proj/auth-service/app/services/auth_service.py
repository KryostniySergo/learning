import logging
import secrets as secrets_lib
from datetime import datetime
from uuid import UUID, uuid4

from app.core.exceptions import (
    AccountAlreadyExistsError,
    InviteAccountMismatchError,
    InviteExpiredError,
    InviteInvalidStatusError,
    InviteNotFoundError,
)
from app.core.outbox import build_outbox_message
from app.core.security import hash_password
from app.models.account import Account
from app.models.company import Company
from app.models.invite import Invite, InviteStatus
from app.models.member import Member
from app.models.member import Role as MemberRole
from app.models.secrets import Secrets
from app.models.user import User
from app.uow import UnitOfWork
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


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

        Является первым шагом флоу регистрации. При успехе генерирует токен
        инвайта и 'отправляет' его на почт.

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
            logger.warning("check_account: IntegrityError on %s: %s", email, exc)
            raise AccountAlreadyExistsError from exc

        logger.info("check_account: invite created for %s (account_id=%s)", email, account.id)
        # "отправка" кода
        logger.debug("[MAIL MOCK] Invite token for %s: %s", email, invite.token)

        return True

    async def sign_up(self, email: str, invite_token: str) -> None:
        """Подтверждает владение почтой по токену инвайта (шаг 2 регистрации).

        Переводит Invite из статуса CREATED в IN_PROGRESS. Это идемпотентный
        относительно guard'ов переход — все проверки статуса выполняются явно,
        чтобы нельзя было пропустить шаг или повторно использовать инвайт.

        Args:
            email (str): почта, для которой выполняется подтверждение.
            invite_token (str): токен инвайта, полученный на шаге 1.

        Raises:
            InviteNotFoundError: если инвайт с таким токеном не существует.
            InviteAccountMismatchError: если токен не относится к указанной почте.
            InviteExpiredError: если срок действия инвайта истёк.
            InviteInvalidStatusError: если инвайт не в статусе CREATED
                (уже подтверждён, завершён или помечен как FAILED).
        """
        invite = await self.uow.invites.get_by_token(invite_token)
        if invite is None:
            logger.warning("sign_up: invite not found for token")
            raise InviteNotFoundError

        account = await self.uow.accounts.get_by_email(email)
        if account is None or invite.account_id != account.id:
            logger.warning("sign_up: token/account mismatch for %s", email)
            raise InviteAccountMismatchError

        if invite.expires_at < datetime.now():
            invite.status = InviteStatus.FAILED
            await self.uow.commit()
            logger.info("sign_up: invite expired for %s", email)
            raise InviteExpiredError

        if invite.status != InviteStatus.CREATED:
            logger.warning("sign_up: invalid invite status %s for %s", invite.status, email)
            raise InviteInvalidStatusError

        invite.status = InviteStatus.IN_PROGRESS
        await self.uow.commit()
        logger.info("sign_up: invite confirmed for %s", email)

    async def sign_up_complete(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        company_name: str,
    ) -> tuple[UUID, UUID]:
        """Завершает регистрацию компании (шаг 3).

        Создаёт Company, User-администратора, Member (роль ADMIN) и Secrets
        одной транзакцией. Переводит Invite в статус COMPLETED. Публикует
        события company.created и employee.created через transactional outbox.

        Args:
            email (str): почта, для которой проходит регистрация.
            password (str): пароль в открытом виде — будет захеширован.
            first_name (str): имя администратора.
            last_name (str): фамилия администратора.
            company_name (str): название создаваемой компании.

        Returns:
            tuple[UUID, UUID]: (company_id, user_id) созданных сущностей.

        Raises:
            InviteNotFoundError: если для этой почты нет активного инвайта.
            InviteInvalidStatusError: если инвайт не в статусе IN_PROGRESS
                (шаг 2 не был пройден, либо регистрация уже завершена).
        """
        account = await self.uow.accounts.get_by_email(email)
        if account is None:
            logger.warning("sign_up_complete: account not found for %s", email)
            raise InviteNotFoundError

        invite = await self.uow.invites.get_by_account_id(account.id)
        if invite is None:
            logger.warning("sign_up_complete: invite not found for %s", email)
            raise InviteNotFoundError

        if invite.status != InviteStatus.IN_PROGRESS:
            logger.warning("sign_up_complete: invalid invite status %s for %s", invite.status, email)
            raise InviteInvalidStatusError

        company = Company(id=uuid4(), name=company_name)
        self.uow.companies.add(company)

        user = User(id=uuid4(), name=first_name, surname=last_name)
        self.uow.users.add(user)

        await self.uow.session.flush()  # явный flush нужен, чтобы User гарантированно был вставлен в БД раньше, чем UPDATE invite сошлётся на его id через user_id (FK)

        member = Member(
            id=uuid4(),
            user_id=user.id,
            company_id=company.id,
            role=MemberRole.ADMIN,
        )
        self.uow.members.add(member)

        secrets_obj = Secrets(
            id=uuid4(),
            user_id=user.id,
            account_id=account.id,
            password_hash=hash_password(password),
        )
        self.uow.secrets.add(secrets_obj)

        invite.status = InviteStatus.COMPLETED
        invite.user_id = user.id

        self.uow.outbox.add(
            build_outbox_message(
                event_type="company.created",
                aggregate_id=company.id,
                payload={
                    "company_id": str(company.id),
                    "name": company.name,
                },
            )
        )
        self.uow.outbox.add(
            build_outbox_message(
                event_type="employee.created",
                aggregate_id=user.id,
                payload={
                    "employee_id": str(user.id),
                    "name": user.name,
                    "surname": user.surname,
                    "company_id": str(company.id),
                },
            )
        )

        await self.uow.commit()
        logger.info("sign_up_complete: company=%s user=%s created for %s", company.id, user.id, email)

        return company.id, user.id
