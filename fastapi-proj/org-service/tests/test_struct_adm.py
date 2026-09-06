import pytest
from httpx import AsyncClient
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_create_root_and_children_builds_ltree_path(
    client: AsyncClient, replica: dict
) -> None:
    """Пути дочерних узлов наращиваются относительно родительского."""
    root = await client.post(
        "/org/api/v1/struct-adm/root",
        headers=replica["admin_headers"],
        json={"name": "Головной офис"},
    )
    assert root.status_code == 201
    root_path = root.json()["path"]
    assert root_path.startswith("n_")
    assert "." not in root_path

    child = await client.post(
        "/org/api/v1/struct-adm/child",
        headers=replica["admin_headers"],
        json={"parent_id": root.json()["id"], "name": "Разработка"},
    )
    assert child.status_code == 201
    child_path = child.json()["path"]
    assert child_path.startswith(f"{root_path}.")

    grandchild = await client.post(
        "/org/api/v1/struct-adm/child",
        headers=replica["admin_headers"],
        json={"parent_id": child.json()["id"], "name": "Backend"},
    )
    assert grandchild.json()["path"].startswith(f"{child_path}.")


async def test_subtree_returns_only_descendants(
    client: AsyncClient, replica: dict
) -> None:
    """Запрос поддерева возвращает потомков, но не сам узел."""
    root = await client.post(
        "/org/api/v1/struct-adm/root",
        headers=replica["admin_headers"],
        json={"name": "Компания"},
    )
    child = await client.post(
        "/org/api/v1/struct-adm/child",
        headers=replica["admin_headers"],
        json={"parent_id": root.json()["id"], "name": "Отдел"},
    )
    await client.post(
        "/org/api/v1/struct-adm/child",
        headers=replica["admin_headers"],
        json={"parent_id": child.json()["id"], "name": "Группа"},
    )

    subtree = await client.get(
        f"/org/api/v1/struct-adm/{child.json()['id']}/subtree",
        headers=replica["admin_headers"],
    )
    assert subtree.status_code == 200
    names = [node["name"] for node in subtree.json()]
    assert names == ["Группа"]


async def test_delete_removes_whole_subtree(
    client: AsyncClient, replica: dict
) -> None:
    """Удаление узла каскадно скрывает всё его поддерево."""
    root = await client.post(
        "/org/api/v1/struct-adm/root",
        headers=replica["admin_headers"],
        json={"name": "Компания"},
    )
    child = await client.post(
        "/org/api/v1/struct-adm/child",
        headers=replica["admin_headers"],
        json={"parent_id": root.json()["id"], "name": "Отдел"},
    )
    await client.post(
        "/org/api/v1/struct-adm/child",
        headers=replica["admin_headers"],
        json={"parent_id": child.json()["id"], "name": "Группа"},
    )

    deleted = await client.delete(
        f"/org/api/v1/struct-adm/{child.json()['id']}",
        headers=replica["admin_headers"],
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted_count"] == 2

    tree = await client.get("/org/api/v1/struct-adm/", headers=replica["admin_headers"])
    assert [node["name"] for node in tree.json()] == ["Компания"]


async def test_assign_manager(client: AsyncClient, replica: dict) -> None:
    """Руководителем можно назначить сотрудника из своей компании."""
    root = await client.post(
        "/org/api/v1/struct-adm/root",
        headers=replica["admin_headers"],
        json={"name": "Компания"},
    )

    response = await client.put(
        f"/org/api/v1/struct-adm/{root.json()['id']}/manager",
        headers=replica["admin_headers"],
        json={"manager_id": str(replica["user_id"])},
    )
    assert response.status_code == 200
    assert response.json()["manager_id"] == str(replica["user_id"])


async def test_regular_user_cannot_modify_structure(
    client: AsyncClient, replica: dict
) -> None:
    """Обычный сотрудник не может менять оргструктуру, но может её читать."""
    create = await client.post(
        "/org/api/v1/struct-adm/root",
        headers=replica["user_headers"],
        json={"name": "Самозванец"},
    )
    assert create.status_code == 403

    read = await client.get("/org/api/v1/struct-adm/", headers=replica["user_headers"])
    assert read.status_code == 200


async def test_requests_without_token_are_rejected(client: AsyncClient) -> None:
    """Без токена оргструктура недоступна."""
    response = await client.get("/org/api/v1/struct-adm/")
    assert response.status_code == 401


async def test_cross_company_access_returns_not_found(
    client: AsyncClient, replica: dict, session
) -> None:
    """Узел чужой компании выглядит как несуществующий."""
    from uuid import uuid4

    from tests.conftest import make_token

    root = await client.post(
        "/org/api/v1/struct-adm/root",
        headers=replica["admin_headers"],
        json={"name": "Своя компания"},
    )

    other_company = uuid4()
    other_user = uuid4()
    await session.execute(
        text("INSERT INTO company (id, name) VALUES (:id, 'Чужая')"),
        {"id": other_company},
    )
    await session.commit()

    other_headers = {
        "Authorization": f"Bearer {make_token(other_user, other_company, 'admin')}"
    }

    response = await client.get(
        f"/org/api/v1/struct-adm/{root.json()['id']}/subtree", headers=other_headers
    )
    assert response.status_code == 404
