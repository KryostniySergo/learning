from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy_utils import Ltree

from app.core.ltree_utils import build_child_path, build_root_path
from app.models.struct_adm import StructAdm
from app.repositories.base import BaseRepository


class StructAdmRepository(BaseRepository[StructAdm]):
    model = StructAdm

    def create_root(self, name: str, company_id: PyUUID) -> StructAdm:
        """Создаёт корневой узел оргструктуры компании (без родителя).

        Args:
            name (str): человекочитаемое название подразделения.
            company_id (PyUUID): id компании, к которой относится узел.

        Returns:
            StructAdm: созданный узел (уже добавлен в сессию, но не закоммичен).
        """
        node_id = uuid4()
        node = StructAdm(
            id=node_id,
            name=name,
            path=Ltree(build_root_path(node_id)),
            company_id=company_id,
        )
        self.add(node)
        return node

    def create_child(self, parent: StructAdm, name: str) -> StructAdm:
        """Создаёт дочерний узел под указанным родителем.

        Args:
            parent (StructAdm): родительский узел (уже загруженный из БД).
            name (str): человекочитаемое название подразделения.

        Returns:
            StructAdm: созданный узел (уже добавлен в сессию, но не закоммичен).
        """
        node_id = uuid4()
        node = StructAdm(
            id=node_id,
            name=name,
            path=Ltree(build_child_path(str(parent.path), node_id)),
            company_id=parent.company_id,
        )
        self.add(node)
        return node

    async def get_descendants(self, path: Ltree, include_self: bool = False) -> list[StructAdm]:
        """Находит все неудалённые узлы внутри поддерева заданного пути.

        Args:
            path (Ltree): путь узла, поддерево которого нужно получить.
            include_self (bool): включать ли сам узел с этим path в результат.

        Returns:
            list[StructAdm]: узлы поддерева, отсортированные по глубине пути.
        """
        query = select(StructAdm).where(StructAdm.path.descendant_of(path)).where(StructAdm.deleted_at.is_(None))
        if not include_self:
            query = query.where(StructAdm.path != path)
        query = query.order_by(StructAdm.path)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_ancestors(self, path: Ltree) -> list[StructAdm]:
        """Находит всех неудалённых предков узла (путь от корня до родителя).

        Args:
            path (Ltree): путь узла, чьих предков нужно получить.

        Returns:
            list[StructAdm]: узлы-предки, отсортированные от корня к листу.
        """
        query = (
            select(StructAdm)
            .where(StructAdm.path.ancestor_of(path))
            .where(StructAdm.path != path)
            .where(StructAdm.deleted_at.is_(None))
            .order_by(StructAdm.path)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_company(self, company_id: PyUUID) -> list[StructAdm]:
        """Находит все неудалённые узлы оргструктуры конкретной компании.

        Args:
            company_id (PyUUID): id компании.

        Returns:
            list[StructAdm]: все узлы компании, отсортированные по пути.
        """
        query = (
            select(StructAdm)
            .where(StructAdm.company_id == company_id)
            .where(StructAdm.deleted_at.is_(None))
            .order_by(StructAdm.path)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
