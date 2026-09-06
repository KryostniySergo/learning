import pytest
from httpx import AsyncClient
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_registration_writes_events_to_outbox(
    client: AsyncClient, session, registered_company: dict
) -> None:
    """Завершение регистрации кладёт события в outbox в той же транзакции."""
    rows = await session.execute(
        text("SELECT event_type, status, topic FROM outbox_message ORDER BY occurred_at")
    )
    events = [(row[0], row[1], row[2]) for row in rows]

    types = [event[0] for event in events]
    assert "company.created" in types
    assert "employee.created" in types

    for _, status, topic in events:
        assert status == "CREATED"
        assert topic == "auth-events"


async def test_outbox_envelope_contains_contract_fields(
    client: AsyncClient, session, registered_company: dict
) -> None:
    """Envelope события содержит все поля контракта."""
    payload = await session.scalar(
        text("SELECT payload FROM outbox_message WHERE event_type = 'company.created'")
    )
    assert set(payload) >= {
        "event_id",
        "event_type",
        "schema_version",
        "producer",
        "payload",
    }
    assert payload["producer"] == "auth-service"
    assert payload["schema_version"] == 1
