import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_position_lifecycle(client: AsyncClient, replica: dict) -> None:
    """Должность создаётся, привязывается к подразделению и сотруднику."""
    position = await client.post(
        "/org/api/v1/positions/",
        headers=replica["admin_headers"],
        json={"title": "Разработчик"},
    )
    assert position.status_code == 201
    position_id = position.json()["id"]

    root = await client.post(
        "/org/api/v1/struct-adm/root",
        headers=replica["admin_headers"],
        json={"name": "Компания"},
    )

    link = await client.post(
        f"/org/api/v1/positions/struct-adm/{root.json()['id']}",
        headers=replica["admin_headers"],
        json={"position_id": position_id},
    )
    assert link.status_code == 201

    assign = await client.post(
        f"/org/api/v1/positions/{position_id}/users",
        headers=replica["admin_headers"],
        json={"user_id": str(replica["user_id"])},
    )
    assert assign.status_code == 201

    assignments = await client.get(
        f"/org/api/v1/positions/users/{replica['user_id']}",
        headers=replica["admin_headers"],
    )
    assert len(assignments.json()) == 1


async def test_duplicate_assignment_is_rejected(
    client: AsyncClient, replica: dict
) -> None:
    """Повторное назначение на ту же должность возвращает конфликт."""
    position = await client.post(
        "/org/api/v1/positions/",
        headers=replica["admin_headers"],
        json={"title": "Аналитик"},
    )
    position_id = position.json()["id"]

    first = await client.post(
        f"/org/api/v1/positions/{position_id}/users",
        headers=replica["admin_headers"],
        json={"user_id": str(replica["user_id"])},
    )
    assert first.status_code == 201

    second = await client.post(
        f"/org/api/v1/positions/{position_id}/users",
        headers=replica["admin_headers"],
        json={"user_id": str(replica["user_id"])},
    )
    assert second.status_code == 409


async def test_deleting_position_releases_assignments(
    client: AsyncClient, replica: dict
) -> None:
    """Удаление должности снимает с неё всех сотрудников."""
    position = await client.post(
        "/org/api/v1/positions/",
        headers=replica["admin_headers"],
        json={"title": "Временная"},
    )
    position_id = position.json()["id"]

    await client.post(
        f"/org/api/v1/positions/{position_id}/users",
        headers=replica["admin_headers"],
        json={"user_id": str(replica["user_id"])},
    )

    deleted = await client.delete(
        f"/org/api/v1/positions/{position_id}", headers=replica["admin_headers"]
    )
    assert deleted.status_code == 204

    assignments = await client.get(
        f"/org/api/v1/positions/users/{replica['user_id']}",
        headers=replica["admin_headers"],
    )
    assert assignments.json() == []


async def test_unknown_employee_cannot_be_assigned(
    client: AsyncClient, replica: dict
) -> None:
    """Сотрудника, которого нет в реплике, назначить нельзя."""
    from uuid import uuid4

    position = await client.post(
        "/org/api/v1/positions/",
        headers=replica["admin_headers"],
        json={"title": "Должность"},
    )

    response = await client.post(
        f"/org/api/v1/positions/{position.json()['id']}/users",
        headers=replica["admin_headers"],
        json={"user_id": str(uuid4())},
    )
    assert response.status_code == 404
