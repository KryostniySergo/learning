from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Общая логика доступа к данным, специфичная логика — в наследниках."""

    model: type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует репозиторий.

        Args:
            session (AsyncSession): активная сессия SQLAlchemy, общая для всех
                репозиториев в рамках одного Unit of Work.
        """
        self.session = session

    async def get_by_id(self, id_: UUID) -> ModelType | None:
        """Находит запись по первичному ключу.

        Args:
            id_ (UUID): идентификатор записи.

        Returns:
            ModelType | None: найденный объект, либо None, если не существует.
        """
        return await self.session.get(self.model, id_)

    def add(self, obj: ModelType) -> None:
        """Добавляет новый объект в сессию (без commit).

        Args:
            obj (ModelType): объект модели, который нужно сохранить.
        """
        self.session.add(obj)
