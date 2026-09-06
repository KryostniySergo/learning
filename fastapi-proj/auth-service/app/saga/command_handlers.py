import logging
from uuid import UUID

from app.core.config import settings
from app.core.event_types import EventType
from app.core.outbox import build_outbox_message
from app.models.invite import InviteStatus
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


class AuthCommandHandler:
    """Выполняет команды саги, адресованные auth-service.

    Не знает о сценарии саги — только выполняет действие и отвечает.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        """Инициализирует обработчик.

        Args:
            uow (UnitOfWork): единица работы, дающая доступ к репозиториям и транзакции.
        """
        self.uow = uow

    async def handle(self, event_type: str, payload: dict) -> None:
        """Направляет команду в нужный обработчик.

        Args:
            event_type (str): тип команды.
            payload (dict): данные команды.
        """
        if event_type == EventType.AUTH_INVALIDATE_INVITE.value:
            await self._invalidate_invite(payload)
            return

        logger.debug("command %s is not for auth-service, skipping", event_type)

    async def _invalidate_invite(self, payload: dict) -> None:
        """Помечает инвайт недействительным и отвечает оркестратору.

        Args:
            payload (dict): данные команды с saga_id, employee_id и invite_id.
        """
        saga_id = UUID(payload["saga_id"])
        employee_id = UUID(payload["employee_id"])
        invite_id = UUID(payload["invite_id"])

        invite = await self.uow.invites.get_by_id(invite_id)
        if invite is not None:
            invite.status = InviteStatus.FAILED

        self.uow.outbox.add(
            build_outbox_message(
                event_type=EventType.AUTH_INVITE_INVALIDATED,
                aggregate_id=employee_id,
                payload={"saga_id": str(saga_id), "employee_id": str(employee_id)},
                topic=settings.kafka_saga_replies_topic,
            )
        )

        await self.uow.commit()
        logger.info("invite %s invalidated by saga %s", invite_id, saga_id)
