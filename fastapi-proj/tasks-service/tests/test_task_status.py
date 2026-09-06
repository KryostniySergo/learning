import pytest
from httpx import AsyncClient
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def create_task(client: AsyncClient, replica: dict) -> str:
    """Создаёт задачу и возвращает её идентификатор.

    Args:
        client (AsyncClient): HTTP-клиент.
        replica (dict): данные реплики с заголовками авторизации.

    Returns:
        str: идентификатор созданной задачи.
    """
    response = await client.post(
        "/tasks/api/v1/tasks/",
        headers=replica["author_headers"],
        json={"title": "Задача", "responsible_id": str(replica["author_id"])},
    )
    return response.json()["id"]


async def test_allowed_status_transitions(client: AsyncClient, replica: dict) -> None:
    """Разрешённая последовательность переходов проходит успешно."""
    task_id = await create_task(client, replica)

    to_progress = await client.put(
        f"/tasks/api/v1/tasks/{task_id}/status",
        headers=replica["author_headers"],
        json={"status": "in_progress"},
    )
    assert to_progress.json()["status"] == "in_progress"

    to_done = await client.put(
        f"/tasks/api/v1/tasks/{task_id}/status",
        headers=replica["author_headers"],
        json={"status": "done"},
    )
    assert to_done.json()["status"] == "done"


async def test_backward_transition_is_rejected(
    client: AsyncClient, replica: dict
) -> None:
    """Возврат статуса назад запрещён guard'ом."""
    task_id = await create_task(client, replica)

    await client.put(
        f"/tasks/api/v1/tasks/{task_id}/status",
        headers=replica["author_headers"],
        json={"status": "in_progress"},
    )

    response = await client.put(
        f"/tasks/api/v1/tasks/{task_id}/status",
        headers=replica["author_headers"],
        json={"status": "new"},
    )
    assert response.status_code == 409


async def test_done_is_terminal(client: AsyncClient, replica: dict) -> None:
    """Из завершённой задачи нельзя перейти ни в какой статус."""
    task_id = await create_task(client, replica)

    await client.put(
        f"/tasks/api/v1/tasks/{task_id}/status",
        headers=replica["author_headers"],
        json={"status": "in_progress"},
    )
    await client.put(
        f"/tasks/api/v1/tasks/{task_id}/status",
        headers=replica["author_headers"],
        json={"status": "done"},
    )

    response = await client.put(
        f"/tasks/api/v1/tasks/{task_id}/status",
        headers=replica["author_headers"],
        json={"status": "in_progress"},
    )
    assert response.status_code == 409


async def test_status_change_writes_outbox_event(
    client: AsyncClient, replica: dict, session
) -> None:
    """Смена статуса кладёт событие task.status_changed в outbox."""
    task_id = await create_task(client, replica)

    await client.put(
        f"/tasks/api/v1/tasks/{task_id}/status",
        headers=replica["author_headers"],
        json={"status": "in_progress"},
    )

    payload = await session.scalar(
        text("SELECT payload FROM outbox_message WHERE event_type = 'task.status_changed'")
    )
    assert payload is not None
    assert payload["payload"]["old_status"] == "new"
    assert payload["payload"]["new_status"] == "in_progress"


async def test_only_author_responsible_or_admin_can_modify(
    client: AsyncClient, replica: dict
) -> None:
    """Посторонний сотрудник не может менять задачу, админ может."""
    task_id = await create_task(client, replica)

    stranger = await client.patch(
        f"/tasks/api/v1/tasks/{task_id}",
        headers=replica["other_headers"],
        json={"title": "Чужая правка"},
    )
    assert stranger.status_code == 403

    admin = await client.patch(
        f"/tasks/api/v1/tasks/{task_id}",
        headers=replica["admin_headers"],
        json={"title": "Правка админа"},
    )
    assert admin.status_code == 200
