from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Репозиторий для работы с сотрудниками (реплика из auth-service)."""

    model = User
