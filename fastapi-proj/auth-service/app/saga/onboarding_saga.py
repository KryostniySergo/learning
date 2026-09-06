import logging
from uuid import uuid4

from app.core.config import settings
from app.core.event_types import EventType
from app.core.outbox import build_outbox_message
from app.models.saga_instance import SagaInstance, SagaStatus, SagaStep
from app.schemas.saga import EmployeeRegisteredPayload, SagaReplyPayload
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


class OnboardingSaga:
    """Оркестратор саги онбординга сотрудника.

    Знает весь сценарий целиком: привязка к подразделению в org-service,
    затем создание приветственной задачи в tasks-service. При провале любого
    шага запускает компенсации в обратном порядке. Сервисы-исполнители
    о саге ничего не знают — они лишь выполняют команды и отвечают.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        """Инициализирует оркестратор.

        Args:
            uow (UnitOfWork): единица работы, дающая доступ к репозиториям и транзакции.
        """
        self.uow = uow

    async def start(self, payload: dict) -> None:
        """Запускает сагу по событию employee.registered.

        Args:
            payload (dict): payload события с данными сотрудника и инвайта.
        """
        data = EmployeeRegisteredPayload(**payload)

        existing = await self.uow.saga.get_running_by_employee(data.employee_id)
        if existing is not None:
            logger.info("saga for employee %s already running, skipping", data.employee_id)
            return

        if data.struct_adm_id is None:
            logger.info(
                "employee %s registered without struct_adm, onboarding not needed",
                data.employee_id,
            )
            return

        saga = SagaInstance(
            id=uuid4(),
            employee_id=data.employee_id,
            company_id=data.company_id,
            invite_id=data.invite_id,
            struct_adm_id=data.struct_adm_id,
            position_id=data.position_id,
            current_step=SagaStep.ORG_ASSIGN_SENT,
            status=SagaStatus.RUNNING,
        )
        self.uow.saga.add(saga)

        self._send_command(
            EventType.ORG_ASSIGN_EMPLOYEE,
            saga,
            {
                "saga_id": str(saga.id),
                "employee_id": str(saga.employee_id),
                "company_id": str(saga.company_id),
                "struct_adm_id": str(saga.struct_adm_id),
                "position_id": str(saga.position_id) if saga.position_id else None,
            },
        )

        await self.uow.commit()
        logger.info("saga %s started for employee %s", saga.id, saga.employee_id)

    async def handle_reply(self, event_type: str, payload: dict) -> None:
        """Обрабатывает ответ исполнителя и переводит сагу на следующий шаг.

        Args:
            event_type (str): тип ответа, определяющий ветку сценария.
            payload (dict): payload ответа с saga_id и данными.
        """
        data = SagaReplyPayload(**payload)

        saga = await self.uow.saga.get_by_id(data.saga_id)
        if saga is None:
            logger.warning("reply %s for unknown saga %s", event_type, data.saga_id)
            return

        handlers = {
            EventType.ORG_EMPLOYEE_ASSIGNED.value: self._on_org_assigned,
            EventType.ORG_EMPLOYEE_ASSIGNMENT_FAILED.value: self._on_org_assign_failed,
            EventType.TASKS_WELCOME_TASK_CREATED.value: self._on_task_created,
            EventType.TASKS_WELCOME_TASK_FAILED.value: self._on_task_failed,
            EventType.ORG_EMPLOYEE_UNASSIGNED.value: self._on_org_unassigned,
            EventType.AUTH_INVITE_INVALIDATED.value: self._on_invite_invalidated,
        }

        handler = handlers.get(event_type)
        if handler is None:
            logger.warning("no saga handler for reply %s", event_type)
            return

        await handler(saga, data)
        await self.uow.commit()

    async def _on_org_assigned(self, saga: SagaInstance, data: SagaReplyPayload) -> None:
        """Шаг 1 успешен — просит tasks-service создать приветственную задачу.

        Args:
            saga (SagaInstance): состояние саги.
            data (SagaReplyPayload): данные ответа.
        """
        if not self._guard(saga, SagaStep.ORG_ASSIGN_SENT):
            return

        saga.current_step = SagaStep.TASK_CREATE_SENT
        self._send_command(
            EventType.TASKS_CREATE_WELCOME_TASK,
            saga,
            {
                "saga_id": str(saga.id),
                "employee_id": str(saga.employee_id),
                "company_id": str(saga.company_id),
            },
        )
        logger.info("saga %s: org assigned, requesting welcome task", saga.id)

    async def _on_org_assign_failed(self, saga: SagaInstance, data: SagaReplyPayload) -> None:
        """Шаг 1 провалился — компенсация ограничивается отменой инвайта.

        Args:
            saga (SagaInstance): состояние саги.
            data (SagaReplyPayload): данные ответа с причиной ошибки.
        """
        if not self._guard(saga, SagaStep.ORG_ASSIGN_SENT):
            return

        saga.status = SagaStatus.COMPENSATING
        saga.current_step = SagaStep.COMPENSATING_INVITE
        saga.error = data.error

        self._send_invalidate_invite(saga)
        logger.warning("saga %s: org assign failed (%s), compensating", saga.id, data.error)

    async def _on_task_created(self, saga: SagaInstance, data: SagaReplyPayload) -> None:
        """Шаг 2 успешен — сага завершена.

        Args:
            saga (SagaInstance): состояние саги.
            data (SagaReplyPayload): данные ответа.
        """
        if not self._guard(saga, SagaStep.TASK_CREATE_SENT):
            return

        saga.current_step = SagaStep.COMPLETED
        saga.status = SagaStatus.COMPLETED
        logger.info("saga %s completed for employee %s", saga.id, saga.employee_id)

    async def _on_task_failed(self, saga: SagaInstance, data: SagaReplyPayload) -> None:
        """Шаг 2 провалился — откатывает привязку в org-service.

        Args:
            saga (SagaInstance): состояние саги.
            data (SagaReplyPayload): данные ответа с причиной ошибки.
        """
        if not self._guard(saga, SagaStep.TASK_CREATE_SENT):
            return

        saga.status = SagaStatus.COMPENSATING
        saga.current_step = SagaStep.COMPENSATING_ORG
        saga.error = data.error

        self._send_command(
            EventType.ORG_UNASSIGN_EMPLOYEE,
            saga,
            {
                "saga_id": str(saga.id),
                "employee_id": str(saga.employee_id),
                "struct_adm_id": str(saga.struct_adm_id),
                "position_id": str(saga.position_id) if saga.position_id else None,
            },
        )
        logger.warning("saga %s: task creation failed (%s), compensating", saga.id, data.error)

    async def _on_org_unassigned(self, saga: SagaInstance, data: SagaReplyPayload) -> None:
        """Откат привязки выполнен — переходит к отмене инвайта.

        Args:
            saga (SagaInstance): состояние саги.
            data (SagaReplyPayload): данные ответа.
        """
        if not self._guard(saga, SagaStep.COMPENSATING_ORG):
            return

        saga.current_step = SagaStep.COMPENSATING_INVITE
        self._send_invalidate_invite(saga)
        logger.info("saga %s: org unassigned, invalidating invite", saga.id)

    async def _on_invite_invalidated(self, saga: SagaInstance, data: SagaReplyPayload) -> None:
        """Компенсация завершена полностью.

        Args:
            saga (SagaInstance): состояние саги.
            data (SagaReplyPayload): данные ответа.
        """
        if not self._guard(saga, SagaStep.COMPENSATING_INVITE):
            return

        saga.current_step = SagaStep.COMPENSATED
        saga.status = SagaStatus.COMPENSATED
        logger.info("saga %s fully compensated", saga.id)

    def _send_invalidate_invite(self, saga: SagaInstance) -> None:
        """Отправляет auth-service команду пометить инвайт недействительным.

        Args:
            saga (SagaInstance): состояние саги.
        """
        self._send_command(
            EventType.AUTH_INVALIDATE_INVITE,
            saga,
            {
                "saga_id": str(saga.id),
                "employee_id": str(saga.employee_id),
                "invite_id": str(saga.invite_id),
            },
        )

    def _send_command(self, event_type: EventType, saga: SagaInstance, payload: dict) -> None:
        """Кладёт команду саги в outbox для публикации в топик команд.

        Args:
            event_type (EventType): тип команды.
            saga (SagaInstance): состояние саги — источник ключа партиционирования.
            payload (dict): данные команды.
        """
        self.uow.outbox.add(
            build_outbox_message(
                event_type=event_type,
                aggregate_id=saga.employee_id,
                payload=payload,
                topic=settings.kafka_saga_commands_topic,
            )
        )

    def _guard(self, saga: SagaInstance, expected_step: SagaStep) -> bool:
        """Проверяет, что сага находится на ожидаемом шаге.

        Защищает от повторной доставки ответа и от ответов, пришедших не вовремя.

        Args:
            saga (SagaInstance): состояние саги.
            expected_step (SagaStep): шаг, на котором сага должна находиться.

        Returns:
            bool: True, если переход допустим.
        """
        if saga.current_step != expected_step:
            logger.info(
                "saga %s: ignoring reply, expected step %s but current is %s",
                saga.id,
                expected_step,
                saga.current_step,
            )
            return False
        return True
