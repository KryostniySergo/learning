import asyncio
import logging

from app.core.config import settings
from app.models.saga_instance import SagaInstance, SagaStatus, SagaStep
from app.saga.onboarding_saga import OnboardingSaga
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


class SagaWatchdog:
    """Отслеживает саги, застрявшие без ответа исполнителя.

    Исполнитель может не ответить: упасть, потерять сообщение или отбраковать
    команду в DLQ. Без сторожа такая сага осталась бы в RUNNING навсегда.
    """

    def __init__(self) -> None:
        """Инициализирует сторож."""
        self._running = False

    async def run_forever(self) -> None:
        """Периодически проверяет наличие зависших саг."""
        self._running = True
        logger.info(
            "SagaWatchdog started: timeout %ds, interval %ds",
            settings.saga_timeout_seconds,
            settings.saga_watchdog_interval_seconds,
        )

        while self._running:
            try:
                await self._check_stale()
            except Exception:
                logger.exception("SagaWatchdog: check failed")

            await asyncio.sleep(settings.saga_watchdog_interval_seconds)

    def stop(self) -> None:
        """Помечает сторож для остановки после текущей итерации."""
        self._running = False

    async def _check_stale(self) -> None:
        """Находит зависшие саги и запускает для них компенсацию."""
        async with UnitOfWork() as uow:
            stale = await uow.saga.get_stale(settings.saga_timeout_seconds)
            saga_ids = [saga.id for saga in stale]

        if not saga_ids:
            return

        logger.warning("found %d stale sagas", len(saga_ids))

        for saga_id in saga_ids:
            await self._handle_stale(saga_id)

    async def _handle_stale(self, saga_id) -> None:
        """Переводит зависшую сагу к компенсации или помечает провалившейся.

        Args:
            saga_id (UUID): идентификатор саги.
        """
        async with UnitOfWork() as uow:
            saga = await uow.saga.get_by_id(saga_id)
            if saga is None or saga.status not in (
                SagaStatus.RUNNING,
                SagaStatus.COMPENSATING,
            ):
                return

            saga.error = f"timed out on step {saga.current_step.value}"
            orchestrator = OnboardingSaga(uow)

            if saga.current_step == SagaStep.ORG_ASSIGN_SENT:
                await self._compensate_invite_only(saga, orchestrator)
            elif saga.current_step == SagaStep.TASK_CREATE_SENT:
                await self._compensate_org_then_invite(saga, orchestrator)
            else:
                saga.status = SagaStatus.FAILED
                logger.error(
                    "saga %s timed out during compensation on step %s, manual review needed",
                    saga.id,
                    saga.current_step,
                )

            await uow.commit()

    async def _compensate_invite_only(self, saga: SagaInstance, orchestrator: OnboardingSaga) -> None:
        """Запускает компенсацию для саги, зависшей на первом шаге.

        Args:
            saga (SagaInstance): зависшая сага.
            orchestrator (OnboardingSaga): оркестратор для отправки команд.
        """
        saga.status = SagaStatus.COMPENSATING
        saga.current_step = SagaStep.COMPENSATING_INVITE
        orchestrator._send_invalidate_invite(saga)
        logger.warning("saga %s timed out on org assign, compensating invite", saga.id)

    async def _compensate_org_then_invite(self, saga: SagaInstance, orchestrator: OnboardingSaga) -> None:
        """Запускает откат привязки для саги, зависшей на втором шаге.

        Args:
            saga (SagaInstance): зависшая сага.
            orchestrator (OnboardingSaga): оркестратор для отправки команд.
        """
        from app.core.event_types import EventType

        saga.status = SagaStatus.COMPENSATING
        saga.current_step = SagaStep.COMPENSATING_ORG
        orchestrator._send_command(
            EventType.ORG_UNASSIGN_EMPLOYEE,
            saga,
            {
                "saga_id": str(saga.id),
                "employee_id": str(saga.employee_id),
                "struct_adm_id": str(saga.struct_adm_id),
                "position_id": str(saga.position_id) if saga.position_id else None,
            },
        )
        logger.warning("saga %s timed out on task creation, compensating org", saga.id)
