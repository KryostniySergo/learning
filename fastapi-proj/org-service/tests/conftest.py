import os

os.environ["DB_NAME"] = os.environ.get("TEST_DB_NAME", "org_db_test")
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
    "user_position",
    "struct_adm_position",
    "struct_adm",
    "position",
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
    """Создаёт тестовую БД, расширение ltree и схему один раз на сессию.

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
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS ltree"))
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_struct_adm_path_gist "
                "ON struct_adm USING GIST (path)"
            )
        )

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
    """Наполняет реплику компанией, администратором и обычным сотрудником.

    Имитирует состояние после обработки событий company.created и employee.created.

    Returns:
        dict: идентификаторы и заголовки авторизации для тестов.
    """
    company_id = uuid4()
    admin_id = uuid4()
    user_id = uuid4()

    async with async_session_maker() as s:
        s.add(Company(id=company_id, name="Тестовая компания"))
        s.add(User(id=admin_id, name="Админ", surname="Тестов", company_id=company_id))
        s.add(User(id=user_id, name="Юзер", surname="Обычный", company_id=company_id))
        await s.commit()

    admin_token = make_token(admin_id, company_id, "admin")
    user_token = make_token(user_id, company_id, "user")

    return {
        "company_id": company_id,
        "admin_id": admin_id,
        "user_id": user_id,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "user_headers": {"Authorization": f"Bearer {user_token}"},
    }
