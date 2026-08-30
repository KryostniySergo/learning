from app.models.users_position import UserPosition
from app.repositories.base import BaseRepository


class UserPositionRepository(BaseRepository[UserPosition]):
    model = UserPosition