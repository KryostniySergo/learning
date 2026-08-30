from app.models.struct_adm_position import StructAdmPosition
from app.repositories.base import BaseRepository


class StructAdmPositionRepository(BaseRepository[StructAdmPosition]):
    model = StructAdmPosition