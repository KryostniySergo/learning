import asyncio
import os

os.environ["DB_NAME"] = os.environ.get("TEST_DB_NAME", "auth_db_test")
os.environ["JWT_SECRET"] = "test-secret-key-for-tests-only-32-bytes"

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command
from app.core.config import settings
from app.db.session import async_session_maker, engine

# переменные должны быть выставлены до импорта app — конфиг читается при импорте
os.environ["DB_NAME"] = os.environ.get("TEST_DB_NAME", "auth_db_test")
os.environ["JWT_SECRET"] = "test-secret-key-for-tests-only-32-bytes"


import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

TABLES_TO_CLEAN = [
    "outbox_message",
    "inbox_message",
    "saga_instance",
    "secrets",
    "invite",
    "member",
    "company",
    "user",
    "account",
]


def run_migrations() -> None:
    """Применяет миграции Alembic к тестовой базе.

    Alembic настроен на асинхронный движок и внутри вызывает asyncio.run(),
    поэтому запускать его напрямую из корутины нельзя. Выполняем в отдельном
    потоке, где своего event loop нет.
    """
    root = Path(__file__).resolve().parent.parent
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(config, "head")


async def run_migrations_in_thread() -> None:
    """Прогоняет миграции, не блокируя текущий event loop."""
    await asyncio.to_thread(run_migrations)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database() -> AsyncIterator[None]:
    """Пересоздаёт тестовую БД и накатывает миграции один раз на сессию.

    Yields:
        None: управление тестам после подготовки схемы.
    """
    admin_url = (
        f"postgresql+asyncpg://{settings.db_user}:{settings.db_pass}@{settings.db_host}:{settings.db_port}/postgres"
    )
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")

    async with admin_engine.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{settings.db_name}" WITH (FORCE)'))
        await conn.execute(text(f'CREATE DATABASE "{settings.db_name}"'))

    await admin_engine.dispose()

    await run_migrations_in_thread()

    yield

    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables() -> AsyncIterator[None]:
    """Очищает таблицы перед каждым тестом, чтобы тесты не влияли друг на друга.

    Yields:
        None: управление тесту после очистки.
    """
    async with async_session_maker() as session:
        for table in TABLES_TO_CLEAN:
            await session.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
        await session.commit()
    yield


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """HTTP-клиент, работающий с приложением напрямую, без реальной сети.

    Yields:
        AsyncClient: клиент для запросов к API.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def session():
    """Сессия БД для проверок состояния внутри тестов.

    Yields:
        AsyncSession: активная сессия.
    """
    async with async_session_maker() as s:
        yield s


@pytest.fixture(autouse=True)
def mock_email(monkeypatch):
    """Отключает реальную отправку писем во всех тестах.

    Args:
        monkeypatch: штатная фикстура pytest для подмены атрибутов.
    """

    async def fake_send(self, to: str, subject: str, body: str) -> None:
        return None

    monkeypatch.setattr("app.adapters.email_sender.EmailSender.send", fake_send)


@pytest_asyncio.fixture
async def registered_company(client: AsyncClient, session) -> dict:
    """Проводит полную регистрацию компании и возвращает её данные.

    Args:
        client (AsyncClient): HTTP-клиент.
        session: сессия БД для получения токена инвайта.

    Returns:
        dict: email, пароль, company_id, user_id и access-токен администратора.
    """
    email = "admin@example.com"
    password = "adminpass123"

    await client.get(f"/auth/api/v1/check_account/{email}")

    token = await session.scalar(text("SELECT token FROM invite ORDER BY created_at DESC LIMIT 1"))

    await client.post("/auth/api/v1/sign-up/", json={"account": email, "invite_token": token})

    response = await client.post(
        "/auth/api/v1/sign-up-complete/",
        json={
            "account": email,
            "pass": password,
            "first_name": "Админ",
            "last_name": "Тестов",
            "company_name": "Тестовая компания",
        },
    )
    data = response.json()

    login = await client.post("/auth/api/v1/login/", json={"account": email, "pass": password})
    access_token = login.json()["access_token"]

    return {
        "email": email,
        "password": password,
        "company_id": data["company_id"],
        "user_id": data["user_id"],
        "token": access_token,
        "headers": {"Authorization": f"Bearer {access_token}"},
    }
