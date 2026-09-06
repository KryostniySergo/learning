import pytest
from httpx import AsyncClient
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_admin_creates_employee_and_employee_registers(
    client: AsyncClient, session, registered_company: dict
) -> None:
    """Администратор заводит сотрудника, тот завершает регистрацию по инвайту."""
    create = await client.post(
        "/auth/api/v1/employees/",
        headers=registered_company["headers"],
        json={
            "account": "worker@example.com",
            "first_name": "Пётр",
            "last_name": "Работников",
        },
    )
    assert create.status_code == 201
    assert create.json()["invite_sent"] is True
    employee_id = create.json()["employee_id"]

    role = await session.scalar(text("SELECT role FROM member WHERE user_id = :uid"), {"uid": employee_id})
    assert role == "USER"

    token = await session.scalar(text("SELECT token FROM invite WHERE user_id = :uid"), {"uid": employee_id})

    register = await client.post(
        "/auth/api/v1/employees/register/",
        json={"invite_token": token, "pass": "workerpass123"},
    )
    assert register.status_code == 200
    assert register.json()["employee_id"] == employee_id

    login = await client.post(
        "/auth/api/v1/login/",
        json={"account": "worker@example.com", "pass": "workerpass123"},
    )
    assert login.status_code == 200


async def test_create_employee_requires_admin_role(client: AsyncClient, session, registered_company: dict) -> None:
    """Обычный сотрудник не может заводить других сотрудников."""
    await client.post(
        "/auth/api/v1/employees/",
        headers=registered_company["headers"],
        json={"account": "plain@example.com", "first_name": "Обычный", "last_name": "Юзер"},
    )
    token = await session.scalar(
        text("SELECT i.token FROM invite i JOIN account a ON a.id = i.account_id WHERE a.email = :email"),
        {"email": "plain@example.com"},
    )
    await client.post(
        "/auth/api/v1/employees/register/",
        json={"invite_token": token, "pass": "plainpass123"},
    )
    login = await client.post("/auth/api/v1/login/", json={"account": "plain@example.com", "pass": "plainpass123"})
    user_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.post(
        "/auth/api/v1/employees/",
        headers=user_headers,
        json={"account": "another@example.com", "first_name": "Ещё", "last_name": "Один"},
    )
    assert response.status_code == 403


async def test_create_employee_requires_authentication(client: AsyncClient) -> None:
    """Без токена создание сотрудника недоступно."""
    response = await client.post(
        "/auth/api/v1/employees/",
        json={"account": "anon@example.com", "first_name": "Аноним", "last_name": "Без"},
    )
    assert response.status_code == 401


async def test_existing_user_is_attached_to_second_company(
    client: AsyncClient, session, registered_company: dict
) -> None:
    """Уже зарегистрированный человек добавляется во вторую компанию без нового инвайта."""
    create = await client.post(
        "/auth/api/v1/employees/",
        headers=registered_company["headers"],
        json={"account": "multi@example.com", "first_name": "Мульти", "last_name": "Компанийный"},
    )
    employee_id = create.json()["employee_id"]

    token = await session.scalar(text("SELECT token FROM invite WHERE user_id = :uid"), {"uid": employee_id})
    await client.post(
        "/auth/api/v1/employees/register/",
        json={"invite_token": token, "pass": "multipass123"},
    )

    second_email = "admin2@example.com"
    await client.get(f"/auth/api/v1/check_account/{second_email}")
    second_token = await session.scalar(
        text("SELECT i.token FROM invite i JOIN account a ON a.id = i.account_id WHERE a.email = :email"),
        {"email": second_email},
    )
    await client.post(
        "/auth/api/v1/sign-up/",
        json={"account": second_email, "invite_token": second_token},
    )
    await client.post(
        "/auth/api/v1/sign-up-complete/",
        json={
            "account": second_email,
            "pass": "admin2pass",
            "first_name": "Второй",
            "last_name": "Админ",
            "company_name": "Вторая компания",
        },
    )
    second_login = await client.post("/auth/api/v1/login/", json={"account": second_email, "pass": "admin2pass"})
    second_headers = {"Authorization": f"Bearer {second_login.json()['access_token']}"}

    attach = await client.post(
        "/auth/api/v1/employees/",
        headers=second_headers,
        json={"account": "multi@example.com", "first_name": "Мульти", "last_name": "Компанийный"},
    )
    assert attach.status_code == 201
    assert attach.json()["employee_id"] == employee_id
    assert attach.json()["invite_sent"] is False

    memberships = await session.scalar(text("SELECT count(*) FROM member WHERE user_id = :uid"), {"uid": employee_id})
    assert memberships == 2
