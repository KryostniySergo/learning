from config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, declared_attr

# SQLite-файл рядом со скриптом — ничего внешнего поднимать не нужно.
# Для PostgreSQL заменить на:
# "postgresql+psycopg://user:password@localhost:5432/bookshop"
DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class BaseModel(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
