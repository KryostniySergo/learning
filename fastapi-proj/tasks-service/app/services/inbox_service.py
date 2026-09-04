import logging
from datetime import datetime
from uuid import uuid4

from app.core.config import settings
from app.core.event_types import EventType
from app.models.company import Company
from app.models.inbox_message import InboxMessage, InboxMessageStatus
from app.models.user import User
from app.schemas.event_envelope import EventEnvelope
from app.schemas.event_payloads import CompanyCreatedPayload, EmployeeCreatedPayload
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


class InboxService:
    """Обрабатывает входящие события Kafka с защитой от повторной обработки."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Инициализирует сервис.

        Args:
            uow (UnitOfWork): единица работы, дающая доступ к репозиториям и транзакции.
        """
        self.uow = uow

    async def handle_event(self, raw_envelope: dict) -> None:
        """Обрабатывает одно событие с проверкой идемпотентности.

        Args:
            raw_envelope (dict): сырой envelope события из Kafka.
        """
        try:
            envelope = EventEnvelope(**raw_envelope)
        except Exception:
            logger.exception("handle_event: invalid envelope, skipping: %s", raw_envelope)
            return

        existing = await self.uow.inbox.get_by_event_id(envelope.event_id)
        if existing is not None:
            logger.info(
                "handle_event: %s (%s) already processed, skipping",
                envelope.event_type,
                envelope.event_id,
            )
            return

        handler = self._get_handler(envelope.event_type)
        if handler is None:
            logger.warning(
                "handle_event: no handler for event_type=%s, skipping", envelope.event_type
            )
            return

        await handler(envelope.payload)

        self.uow.inbox.add(
            InboxMessage(
                id=uuid4(),
                event_id=envelope.event_id,
                event_type=envelope.event_type,
                consumer_name=settings.consumer_name,
                received_at=datetime.now(),
                status=InboxMessageStatus.PROCESSED,
            )
        )

        await self.uow.commit()
        logger.info("handle_event: %s (%s) processed", envelope.event_type, envelope.event_id)

    def _get_handler(self, event_type: str):
        """Возвращает обработчик для данного типа события.

        Args:
            event_type (str): тип события.

        Returns:
            обработчик события, либо None, если тип неизвестен.
        """
        handlers = {
            EventType.COMPANY_CREATED.value: self._handle_company_created,
            EventType.EMPLOYEE_CREATED.value: self._handle_employee_created,
        }
        return handlers.get(event_type)

    async def _handle_company_created(self, payload: dict) -> None:
        """Создаёт локальную реплику Company из события company.created.

        Args:
            payload (dict): payload события.
        """
        data = CompanyCreatedPayload(**payload)

        existing = await self.uow.company.get_by_id(data.company_id)
        if existing is not None:
            logger.info("company %s already in replica, skipping", data.company_id)
            return

        self.uow.company.add(Company(id=data.company_id, name=data.name))

    async def _handle_employee_created(self, payload: dict) -> None:
        """Создаёт локальную реплику User из события employee.created.

        Args:
            payload (dict): payload события.
        """
        data = EmployeeCreatedPayload(**payload)

        existing = await self.uow.user.get_by_id(data.employee_id)
        if existing is not None:
            # сотрудник мог быть добавлен во вторую компанию — реплика хранит
            # только первую, поэтому обновляем лишь имя
            existing.name = data.name
            existing.surname = data.surname
            logger.info("user %s already in replica, updated names only", data.employee_id)
            return

        self.uow.user.add(
            User(
                id=data.employee_id,
                name=data.name,
                surname=data.surname,
                company_id=data.company_id,
            )
        )
