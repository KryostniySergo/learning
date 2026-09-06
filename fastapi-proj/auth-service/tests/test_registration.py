import pytest
from httpx import AsyncClient
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def test_company_registration_full_flow(client: AsyncClient, session) -> None:
    """Проходит все три шага регистрации компании и проверяет созданные сущности."""
    email = "founder@example.com"

    check = await client.get(f"/auth/api/v1/check_account/{email}")
    assert check.status_code == 200
    assert check.json()["available"] is True

    token = await session.scalar(
        text("SELECT token FROM invite WHERE account_id = "
             "(SELECT id FROM account WHERE email = :email)"),
        {"email": email},
    )
    assert token is not None

    sign_up = await client.post(
        "/auth/api/v1/sign-up/", json={"account": email, "invite_token": token}
    )
    assert sign_up.status_code == 200
    assert sign_up.json()["confirmed"] is True

    complete = await client.post(
        "/auth/api/v1/sign-up-complete/",
        json={
            "account": email,
            "pass": "secret123",
            "first_name": "Иван",
            "last_name": "Основатель",
            "company_name": "ООО Ромашка",
        },
    )
    assert complete.status_code == 200
    body = complete.json()
    assert body["company_id"]
    assert body["user_id"]

    role = await session.scalar(
        text("SELECT role FROM member WHERE user_id = :uid"), {"uid": body["user_id"]}
    )
    assert role == "ADMIN"

    invite_status = await session.scalar(
        text("SELECT status FROM invite WHERE account_id = "
             "(SELECT id FROM account WHERE email = :email)"),
        {"email": email},
    )
    assert invite_status == "COMPLETED"


async def test_check_account_rejects_taken_email(client: AsyncClient) -> None:
    """Повторная проверка занятой почты возвращает available=False."""
    email = "taken@example.com"

    first = await client.get(f"/auth/api/v1/check_account/{email}")
    assert first.json()["available"] is True

    second = await client.get(f"/auth/api/v1/check_account/{email}")
    assert second.json()["available"] is False


async def test_check_account_rejects_invalid_email(client: AsyncClient) -> None:
    """Невалидный адрес отклоняется валидацией до бизнес-логики."""
    response = await client.get("/auth/api/v1/check_account/not-an-email")
    assert response.status_code == 422


async def test_sign_up_rejects_unknown_token(client: AsyncClient) -> None:
    """Подтверждение с несуществующим токеном возвращает 404."""
    email = "unknown@example.com"
    await client.get(f"/auth/api/v1/check_account/{email}")

    response = await client.post(
        "/auth/api/v1/sign-up/", json={"account": email, "invite_token": "wrong-token"}
    )
    assert response.status_code == 404


async def test_sign_up_complete_requires_confirmed_invite(
    client: AsyncClient, session
) -> None:
    """Нельзя пропустить шаг подтверждения почты и сразу завершить регистрацию."""
    email = "skipper@example.com"
    await client.get(f"/auth/api/v1/check_account/{email}")

    response = await client.post(
        "/auth/api/v1/sign-up-complete/",
        json={
            "account": email,
            "pass": "secret123",
            "first_name": "Прыгун",
            "last_name": "Через",
            "company_name": "Шаг",
        },
    )
    assert response.status_code == 409


async def test_login_returns_token_with_claims(
    client: AsyncClient, registered_company: dict
) -> None:
    """Логин выдаёт токен, содержащий компанию и роль пользователя."""
    import jwt

    from app.core.config import settings

    payload = jwt.decode(
        registered_company["token"],
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    assert payload["sub"] == registered_company["user_id"]
    assert payload["company_id"] == registered_company["company_id"]
    assert payload["role"] == "admin"


async def test_login_rejects_wrong_password(
    client: AsyncClient, registered_company: dict
) -> None:
    """Неверный пароль возвращает 401 без подробностей о причине."""
    response = await client.post(
        "/auth/api/v1/login/",
        json={"account": registered_company["email"], "pass": "wrong"},
    )
    assert response.status_code == 401
