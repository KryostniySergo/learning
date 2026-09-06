from uuid import uuid4

import pytest
from sqlalchemy import text

from app.services.inbox_service import InboxService
from app.uow import UnitOfWork

pytestmark = pytest.mark.asyncio


def make_envelope(event_type: str, payload: dict) -> dict:
    """Собирает envelope события в том же формате, что публикует auth-service.

    Args:
        event_type (str): тип события.
        payload (dict): полезная нагрузка.

    Returns:
        dict: готовый envelope.
    """
    return {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "schema_version": 1,
        "producer": "auth-service",
        "payload": payload,
    }


async def test_company_created_fills_replica(session) -> None:
    """Событие company.created создаёт локальную реплику компании."""
    company_id = uuid4()
    envelope = make_envelope(
        "company.created", {"company_id": str(company_id), "name": "Новая компания"}
    )

    async with UnitOfWork() as uow:
        await InboxService(uow).handle_event(envelope)

    name = await session.scalar(
        text("SELECT name FROM company WHERE id = :id"), {"id": company_id}
    )
    assert name == "Новая компания"


async def test_duplicate_event_is_processed_once(session) -> None:
    """Повторная доставка того же события не даёт повторного эффекта."""
    company_id = uuid4()
    envelope = make_envelope(
        "company.created", {"company_id": str(company_id), "name": "Компания"}
    )

    async with UnitOfWork() as uow:
        await InboxService(uow).handle_event(envelope)
    async with UnitOfWork() as uow:
        await InboxService(uow).handle_event(envelope)

    companies = await session.scalar(
        text("SELECT count(*) FROM company WHERE id = :id"), {"id": company_id}
    )
    assert companies == 1

    inbox_rows = await session.scalar(
        text("SELECT count(*) FROM inbox_message WHERE event_id = :eid"),
        {"eid": envelope["event_id"]},
    )
    assert inbox_rows == 1


async def test_employee_created_fills_user_replica(session) -> None:
    """Событие employee.created создаёт реплику сотрудника."""
    company_id = uuid4()
    employee_id = uuid4()

    async with UnitOfWork() as uow:
        await InboxService(uow).handle_event(
            make_envelope(
                "company.created", {"company_id": str(company_id), "name": "Компания"}
            )
        )
    async with UnitOfWork() as uow:
        await InboxService(uow).handle_event(
            make_envelope(
                "employee.created",
                {
                    "employee_id": str(employee_id),
                    "name": "Пётр",
                    "surname": "Петров",
                    "company_id": str(company_id),
                },
            )
        )

    surname = await session.scalar(
        text('SELECT surname FROM "user" WHERE id = :id'), {"id": employee_id}
    )
    assert surname == "Петров"


async def test_invalid_envelope_is_skipped_without_crash(session) -> None:
    """Событие с нарушенным контрактом пропускается, не роняя обработчик."""
    broken = {"event_type": "company.created", "payload": {}}

    async with UnitOfWork() as uow:
        await InboxService(uow).handle_event(broken)

    inbox_rows = await session.scalar(text("SELECT count(*) FROM inbox_message"))
    assert inbox_rows == 0


async def test_unknown_event_type_is_ignored(session) -> None:
    """Событие неизвестного типа не обрабатывается и не пишется в inbox."""
    envelope = make_envelope("some.unknown.event", {"foo": "bar"})

    async with UnitOfWork() as uow:
        await InboxService(uow).handle_event(envelope)

    inbox_rows = await session.scalar(text("SELECT count(*) FROM inbox_message"))
    assert inbox_rows == 0
