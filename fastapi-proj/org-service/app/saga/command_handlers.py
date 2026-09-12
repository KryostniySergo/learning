import logging
from datetime import UTC, datetime
from uuid import uuid4

from app.core.config import settings
from app.core.event_types import EventType
from app.core.outbox import build_outbox_message
from app.models.struct_adm_position import StructAdmPosition
from app.models.user_position import UserPosition
from app.schemas.saga_commands import AssignEmployeeCommand, UnassignEmployeeCommand
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


class EmployeeNotReplicatedError(Exception):
    """Сотрудник ещё не появился в локальной реплике.

    Означает, что событие employee.created пока не обработано. Команду нужно
    не проваливать, а дать Kafka передоставить её позже — поэтому исключение
    поднимается наверх и offset не коммитится.
    """


class OrgCommandHandler:
    """Выполняет команды саги, адресованные org-service.

    О сценарии саги не знает — выполняет действие и публикует ответ.
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
        if event_type == EventType.ORG_ASSIGN_EMPLOYEE.value:
            await self._assign_employee(payload)
        elif event_type == EventType.ORG_UNASSIGN_EMPLOYEE.value:
            await self._unassign_employee(payload)
        else:
            logger.debug("command %s is not for org-service, skipping", event_type)

    async def _assign_employee(self, payload: dict) -> None:
        """Привязывает сотрудника к подразделению и должности.

        Args:
            payload (dict): данные команды.

        Raises:
            EmployeeNotReplicatedError: если сотрудника ещё нет в реплике —
                команда будет передоставлена Kafka позже.
        """
        cmd = AssignEmployeeCommand(**payload)

        user = await self.uow.user.get_by_id(cmd.employee_id)
        if user is None:
            logger.info("assign_employee: user %s not in replica yet, will retry", cmd.employee_id)
            raise EmployeeNotReplicatedError

        node = await self.uow.struct_adm.get_by_id(cmd.struct_adm_id)
        if node is None or node.deleted_at is not None:
            await self._reply_failure(cmd, "struct_adm not found")
            return
        if node.company_id != cmd.company_id:
            await self._reply_failure(cmd, "struct_adm belongs to another company")
            return

        if cmd.position_id is not None:
            position = await self.uow.position.get_by_id(cmd.position_id)
            if position is None or position.deleted_at is not None:
                await self._reply_failure(cmd, "position not found")
                return

            link = await self.uow.struct_adm_position.get_link(cmd.struct_adm_id, cmd.position_id)
            if link is None:
                self.uow.struct_adm_position.add(
                    StructAdmPosition(
                        id=uuid4(),
                        struct_adm_id=cmd.struct_adm_id,
                        position_id=cmd.position_id,
                    )
                )

            assignment = await self.uow.user_position.get_link(cmd.employee_id, cmd.position_id)
            if assignment is None:
                self.uow.user_position.add(
                    UserPosition(id=uuid4(), user_id=cmd.employee_id, position_id=cmd.position_id)
                )

        self.uow.outbox.add(
            build_outbox_message(
                event_type=EventType.ORG_EMPLOYEE_ASSIGNED,
                aggregate_id=cmd.employee_id,
                payload={"saga_id": str(cmd.saga_id), "employee_id": str(cmd.employee_id)},
                topic=settings.kafka_saga_replies_topic,
            )
        )

        await self.uow.commit()
        logger.info(
            "employee %s assigned to struct_adm %s by saga %s",
            cmd.employee_id,
            cmd.struct_adm_id,
            cmd.saga_id,
        )

    async def _unassign_employee(self, payload: dict) -> None:
        """Откатывает привязку сотрудника к должности — компенсация.

        Args:
            payload (dict): данные команды.
        """
        cmd = UnassignEmployeeCommand(**payload)

        if cmd.position_id is not None:
            assignment = await self.uow.user_position.get_link(cmd.employee_id, cmd.position_id)
            if assignment is not None:
                assignment.deleted_at = datetime.now(UTC)

        self.uow.outbox.add(
            build_outbox_message(
                event_type=EventType.ORG_EMPLOYEE_UNASSIGNED,
                aggregate_id=cmd.employee_id,
                payload={"saga_id": str(cmd.saga_id), "employee_id": str(cmd.employee_id)},
                topic=settings.kafka_saga_replies_topic,
            )
        )

        await self.uow.commit()
        logger.info("employee %s unassigned by saga %s", cmd.employee_id, cmd.saga_id)

    async def _reply_failure(self, cmd: AssignEmployeeCommand, error: str) -> None:
        """Публикует ответ о невозможности выполнить команду.

        Args:
            cmd (AssignEmployeeCommand): исходная команда.
            error (str): причина отказа.
        """
        self.uow.outbox.add(
            build_outbox_message(
                event_type=EventType.ORG_EMPLOYEE_ASSIGNMENT_FAILED,
                aggregate_id=cmd.employee_id,
                payload={
                    "saga_id": str(cmd.saga_id),
                    "employee_id": str(cmd.employee_id),
                    "error": error,
                },
                topic=settings.kafka_saga_replies_topic,
            )
        )
        await self.uow.commit()
        logger.warning("assign_employee failed for saga %s: %s", cmd.saga_id, error)
