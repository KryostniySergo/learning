from uuid import UUID as PyUUID

from sqlalchemy import select

from app.models.struct_adm_position import StructAdmPosition
from app.repositories.base import BaseRepository


class StructAdmPositionRepository(BaseRepository[StructAdmPosition]):
    model = StructAdmPosition

    async def get_by_struct_adm(self, struct_adm_id: PyUUID) -> list[StructAdmPosition]:
        """Находит все действующие привязки должностей к подразделению.

        Args:
            struct_adm_id (PyUUID): id подразделения.

        Returns:
            list[StructAdmPosition]: привязки подразделение-должность.
        """
        result = await self.session.execute(
            select(StructAdmPosition)
            .where(StructAdmPosition.struct_adm_id == struct_adm_id)
            .where(StructAdmPosition.deleted_at.is_(None))
        )
        return list(result.scalars().all())

    async def get_link(self, struct_adm_id: PyUUID, position_id: PyUUID) -> StructAdmPosition | None:
        """Находит конкретную привязку должности к подразделению.

        Args:
            struct_adm_id (PyUUID): id подразделения.
            position_id (PyUUID): id должности.

        Returns:
            StructAdmPosition | None: найденная привязка, либо None.
        """
        result = await self.session.execute(
            select(StructAdmPosition)
            .where(StructAdmPosition.struct_adm_id == struct_adm_id)
            .where(StructAdmPosition.position_id == position_id)
            .where(StructAdmPosition.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_position(self, position_id: PyUUID) -> list[StructAdmPosition]:
        """Находит все действующие привязки должности к подразделениям.

        Args:
            position_id (PyUUID): id должности.

        Returns:
            list[StructAdmPosition]: привязки этой должности.
        """
        result = await self.session.execute(
            select(StructAdmPosition)
            .where(StructAdmPosition.position_id == position_id)
            .where(StructAdmPosition.deleted_at.is_(None))
        )
        return list(result.scalars().all())
