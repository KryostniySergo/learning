import pytest
from httpx import AsyncClient
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_repeated_sign_up_is_rejected_by_guard(
    client: AsyncClient, session
) -> None:
    """Повторное подтверждение того же инвайта не проходит guard статуса."""
    email = "guard@example.com"
    await client.get(f"/auth/api/v1/check_account/{email}")
    token = await session.scalar(
        text("SELECT i.token FROM invite i JOIN account a ON a.id = i.account_id "
             "WHERE a.email = :email"),
        {"email": email},
    )

    first = await client.post(
        "/auth/api/v1/sign-up/", json={"account": email, "invite_token": token}
    )
    assert first.status_code == 200

    second = await client.post(
        "/auth/api/v1/sign-up/", json={"account": email, "invite_token": token}
    )
    assert second.status_code == 409


async def test_repeated_sign_up_complete_does_not_create_second_company(
    client: AsyncClient, session, registered_company: dict
) -> None:
    """Повторное завершение регистрации не создаёт дубликат компании."""
    before = await session.scalar(text("SELECT count(*) FROM company"))

    response = await client.post(
        "/auth/api/v1/sign-up-complete/",
        json={
            "account": registered_company["email"],
            "pass": "another123",
            "first_name": "Дубль",
            "last_name": "Дублев",
            "company_name": "Дубликат",
        },
    )
    assert response.status_code == 409

    after = await session.scalar(text("SELECT count(*) FROM company"))
    assert after == before


async def test_repeated_employee_registration_is_rejected(
    client: AsyncClient, session, registered_company: dict
) -> None:
    """Инвайт сотрудника нельзя использовать дважды."""
    create = await client.post(
        "/auth/api/v1/employees/",
        headers=registered_company["headers"],
        json={"account": "once@example.com", "first_name": "Один", "last_name": "Раз"},
    )
    employee_id = create.json()["employee_id"]
    token = await session.scalar(
        text("SELECT token FROM invite WHERE user_id = :uid"), {"uid": employee_id}
    )

    first = await client.post(
        "/auth/api/v1/employees/register/",
        json={"invite_token": token, "pass": "oncepass123"},
    )
    assert first.status_code == 200

    second = await client.post(
        "/auth/api/v1/employees/register/",
        json={"invite_token": token, "pass": "oncepass123"},
    )
    assert second.status_code == 409

    secrets_count = await session.scalar(
        text("SELECT count(*) FROM secrets WHERE user_id = :uid"), {"uid": employee_id}
    )
    assert secrets_count == 1
