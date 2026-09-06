import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_task_crud_lifecycle(client: AsyncClient, replica: dict) -> None:
    """Задача создаётся, читается, изменяется и удаляется."""
    create = await client.post(
        "/tasks/api/v1/tasks/",
        headers=replica["author_headers"],
        json={
            "title": "Первая задача",
            "description": "Описание",
            "responsible_id": str(replica["other_id"]),
            "watcher_ids": [str(replica["other_id"])],
            "assignee_ids": [str(replica["author_id"])],
            "estimate_minutes": 120,
        },
    )
    assert create.status_code == 201
    task = create.json()
    assert task["status"] == "new"
    assert task["author_id"] == str(replica["author_id"])

    detail = await client.get(
        f"/tasks/api/v1/tasks/{task['id']}", headers=replica["author_headers"]
    )
    assert detail.status_code == 200
    assert detail.json()["watcher_ids"] == [str(replica["other_id"])]
    assert detail.json()["assignee_ids"] == [str(replica["author_id"])]

    updated = await client.patch(
        f"/tasks/api/v1/tasks/{task['id']}",
        headers=replica["author_headers"],
        json={"title": "Переименованная"},
    )
    assert updated.json()["title"] == "Переименованная"

    deleted = await client.delete(
        f"/tasks/api/v1/tasks/{task['id']}", headers=replica["author_headers"]
    )
    assert deleted.status_code == 204

    after = await client.get(
        f"/tasks/api/v1/tasks/{task['id']}", headers=replica["author_headers"]
    )
    assert after.status_code == 404


async def test_task_participants_must_exist_in_replica(
    client: AsyncClient, replica: dict
) -> None:
    """Нельзя назначить ответственным того, кого нет в реплике."""
    from uuid import uuid4

    response = await client.post(
        "/tasks/api/v1/tasks/",
        headers=replica["author_headers"],
        json={"title": "Задача", "responsible_id": str(uuid4())},
    )
    assert response.status_code == 404


async def test_list_filters_by_status(client: AsyncClient, replica: dict) -> None:
    """Список задач фильтруется по статусу."""
    first = await client.post(
        "/tasks/api/v1/tasks/",
        headers=replica["author_headers"],
        json={"title": "Новая", "responsible_id": str(replica["author_id"])},
    )
    await client.post(
        "/tasks/api/v1/tasks/",
        headers=replica["author_headers"],
        json={"title": "В работе", "responsible_id": str(replica["author_id"])},
    )
    await client.put(
        f"/tasks/api/v1/tasks/{first.json()['id']}/status",
        headers=replica["author_headers"],
        json={"status": "in_progress"},
    )

    in_progress = await client.get(
        "/tasks/api/v1/tasks/?status=in_progress", headers=replica["author_headers"]
    )
    assert len(in_progress.json()) == 1
    assert in_progress.json()[0]["title"] == "Новая"


async def test_requests_without_token_are_rejected(client: AsyncClient) -> None:
    """Без токена задачи недоступны."""
    response = await client.get("/tasks/api/v1/tasks/")
    assert response.status_code == 401
