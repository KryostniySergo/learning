import os

os.environ["DB_NAME"] = os.environ.get("TEST_DB_NAME", "tasks_db_test")
os.environ["JWT_SECRET"] = "test-secret-key-for-tests-only-32-bytes"

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.db.session import async_session_maker, engine
from app.main import app
from app.models.base import Base
from app.models.company import Company
from app.models.user import User

TABLES_TO_CLEAN = [
    "outbox_message",
    "inbox_message",
    "task_watcher",
    "task_assignee",
    "task",
    "user",
    "company",
]


def make_token(user_id: UUID, company_id: UUID, role: str = "admin") -> str:
    """Собирает JWT так же, как это делает auth-service.

    Args:
        user_id (UUID): идентификатор пользователя.
        company_id (UUID): идентификатор компании.
        role (str): роль пользователя.

    Returns:
        str: подписанный токен.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "company_id": str(company_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=30),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.fixture(scope="session")
def event_loop():
    """Единый event loop на всю сессию тестов.

    Yields:
        asyncio.AbstractEventLoop: цикл событий.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database() -> AsyncIterator[None]:
    """Создаёт тестовую БД и схему один раз на сессию.

    Yields:
        None: управление тестам после подготовки схемы.
    """
    admin_url = (
        f"postgresql+asyncpg://{settings.db_user}:{settings.db_pass}"
        f"@{settings.db_host}:{settings.db_port}/postgres"
    )
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")

    async with admin_engine.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": settings.db_name},
        )
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{settings.db_name}"'))

    await admin_engine.dispose()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables() -> AsyncIterator[None]:
    """Очищает таблицы перед каждым тестом.

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
    """HTTP-клиент, работающий с приложением напрямую.

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


@pytest_asyncio.fixture
async def replica() -> dict:
    """Наполняет реплику компанией, автором и вторым сотрудником.

    Returns:
        dict: идентификаторы и заголовки авторизации для тестов.
    """
    company_id = uuid4()
    author_id = uuid4()
    other_id = uuid4()

    async with async_session_maker() as s:
        s.add(Company(id=company_id, name="Тестовая компания"))
        s.add(User(id=author_id, name="Автор", surname="Задачин", company_id=company_id))
        s.add(User(id=other_id, name="Коллега", surname="Соседов", company_id=company_id))
        await s.commit()

    return {
        "company_id": company_id,
        "author_id": author_id,
        "other_id": other_id,
        "author_headers": {
            "Authorization": f"Bearer {make_token(author_id, company_id, 'user')}"
        },
        "other_headers": {
            "Authorization": f"Bearer {make_token(other_id, company_id, 'user')}"
        },
        "admin_headers": {
            "Authorization": f"Bearer {make_token(uuid4(), company_id, 'admin')}"
        },
    }
