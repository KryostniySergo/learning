import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.config import settings
from app.core.event_types import EventType
from app.core.outbox import build_outbox_message
from app.models.task import Task, TaskStatus
from app.models.task_assignee import TaskAssignee
from app.schemas.saga_commands import CreateWelcomeTaskCommand
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)

WELCOME_TASK_TITLE = "Добро пожаловать в компанию"
WELCOME_TASK_DESCRIPTION = "Познакомьтесь с командой, изучите внутренние регламенты и заполните профиль в системе."
WELCOME_TASK_DEADLINE_DAYS = 7
WELCOME_TASK_ESTIMATE_MINUTES = 60


class EmployeeNotReplicatedError(Exception):
    """Сотрудник ещё не появился в локальной реплике.

    Команду нужно не проваливать, а дать Kafka передоставить её позже.
    """


class TasksCommandHandler:
    """Выполняет команды саги, адресованные tasks-service."""

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
        if event_type == EventType.TASKS_CREATE_WELCOME_TASK.value:
            await self._create_welcome_task(payload)
        else:
            logger.debug("command %s is not for tasks-service, skipping", event_type)

    async def _create_welcome_task(self, payload: dict) -> None:
        """Создаёт приветственную задачу для нового сотрудника.

        Автором и ответственным становится сам сотрудник — задача носит
        ознакомительный характер.

        Args:
            payload (dict): данные команды.

        Raises:
            EmployeeNotReplicatedError: если сотрудника ещё нет в реплике.
        """
        cmd = CreateWelcomeTaskCommand(**payload)

        user = await self.uow.user.get_by_id(cmd.employee_id)
        if user is None:
            logger.info("create_welcome_task: user %s not in replica yet, will retry", cmd.employee_id)
            raise EmployeeNotReplicatedError

        company = await self.uow.company.get_by_id(cmd.company_id)
        if company is None:
            await self._reply_failure(cmd, "company not found in replica")
            return

        task = Task(
            id=uuid4(),
            title=WELCOME_TASK_TITLE,
            description=WELCOME_TASK_DESCRIPTION,
            company_id=cmd.company_id,
            author_id=cmd.employee_id,
            responsible_id=cmd.employee_id,
            deadline=datetime.now(UTC) + timedelta(days=WELCOME_TASK_DEADLINE_DAYS),
            estimate_minutes=WELCOME_TASK_ESTIMATE_MINUTES,
            status=TaskStatus.NEW,
        )
        self.uow.task.add(task)
        await self.uow.session.flush()

        self.uow.task_assignee.add(TaskAssignee(id=uuid4(), task_id=task.id, user_id=cmd.employee_id))

        self.uow.outbox.add(
            build_outbox_message(
                event_type=EventType.TASKS_WELCOME_TASK_CREATED,
                aggregate_id=cmd.employee_id,
                payload={
                    "saga_id": str(cmd.saga_id),
                    "employee_id": str(cmd.employee_id),
                    "task_id": str(task.id),
                },
                topic=settings.kafka_saga_replies_topic,
            )
        )

        await self.uow.commit()
        logger.info(
            "welcome task %s created for employee %s by saga %s",
            task.id,
            cmd.employee_id,
            cmd.saga_id,
        )

    async def _reply_failure(self, cmd: CreateWelcomeTaskCommand, error: str) -> None:
        """Публикует ответ о невозможности выполнить команду.

        Args:
            cmd (CreateWelcomeTaskCommand): исходная команда.
            error (str): причина отказа.
        """
        self.uow.outbox.add(
            build_outbox_message(
                event_type=EventType.TASKS_WELCOME_TASK_FAILED,
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
        logger.warning("create_welcome_task failed for saga %s: %s", cmd.saga_id, error)
