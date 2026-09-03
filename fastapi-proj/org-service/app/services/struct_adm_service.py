import logging
from datetime import datetime
from uuid import UUID

from app.core.exceptions import (
    CrossCompanyAccessError,
    NotAuthorizedError,
    ParentNotFoundError,
    StructAdmNotFoundError,
    UserNotFoundError,
)
from app.models.struct_adm import StructAdm
from app.schemas.current_user import CurrentUser
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


class StructAdmService:
    """Бизнес-логика управления организационной структурой компании."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Инициализирует сервис.

        Args:
            uow (UnitOfWork): единица работы, дающая доступ к репозиториям и транзакции.
        """
        self.uow = uow

    async def create_root(self, name: str, current_user: CurrentUser) -> StructAdm:
        """Создаёт корневое подразделение компании текущего пользователя.

        Args:
            name (str): название подразделения.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            StructAdm: созданный узел оргструктуры.

        Raises:
            NotAuthorizedError: если пользователь не администратор компании.
        """
        self._require_admin(current_user)

        node = self.uow.struct_adm.create_root(name=name, company_id=current_user.company_id)
        await self.uow.commit()

        logger.info("create_root: node=%s company=%s", node.id, current_user.company_id)
        return node

    async def create_child(self, parent_id: UUID, name: str, current_user: CurrentUser) -> StructAdm:
        """Создаёт дочернее подразделение под указанным родителем.

        Args:
            parent_id (UUID): id родительского подразделения.
            name (str): название создаваемого подразделения.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            StructAdm: созданный узел оргструктуры.

        Raises:
            NotAuthorizedError: если пользователь не администратор компании.
            ParentNotFoundError: если родительское подразделение не найдено.
            CrossCompanyAccessError: если родитель принадлежит другой компании.
        """
        self._require_admin(current_user)

        parent = await self._get_owned_node(parent_id, current_user, not_found_error=ParentNotFoundError)

        node = self.uow.struct_adm.create_child(parent=parent, name=name)
        await self.uow.commit()

        logger.info("create_child: node=%s parent=%s", node.id, parent_id)
        return node

    async def rename(self, node_id: UUID, name: str, current_user: CurrentUser) -> StructAdm:
        """Переименовывает подразделение.

        Args:
            node_id (UUID): id подразделения.
            name (str): новое название.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            StructAdm: обновлённый узел.

        Raises:
            NotAuthorizedError: если пользователь не администратор компании.
            StructAdmNotFoundError: если подразделение не найдено.
            CrossCompanyAccessError: если подразделение принадлежит другой компании.
        """
        self._require_admin(current_user)

        node = await self._get_owned_node(node_id, current_user)
        node.name = name
        await self.uow.commit()

        logger.info("rename: node=%s new_name=%s", node_id, name)
        return node

    async def assign_manager(self, node_id: UUID, manager_id: UUID, current_user: CurrentUser) -> StructAdm:
        """Назначает руководителя подразделения.

        Args:
            node_id (UUID): id подразделения.
            manager_id (UUID): id сотрудника, назначаемого руководителем.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            StructAdm: обновлённый узел.

        Raises:
            NotAuthorizedError: если пользователь не администратор компании.
            StructAdmNotFoundError: если подразделение не найдено.
            CrossCompanyAccessError: если подразделение или сотрудник из другой компании.
            UserNotFoundError: если сотрудник отсутствует в локальной реплике
                (событие employee.created ещё не обработано).
        """
        self._require_admin(current_user)

        node = await self._get_owned_node(node_id, current_user)

        manager = await self.uow.user.get_by_id(manager_id)
        if manager is None:
            logger.warning("assign_manager: user %s not found in replica", manager_id)
            raise UserNotFoundError
        if manager.company_id != current_user.company_id:
            raise CrossCompanyAccessError

        node.manager_id = manager_id
        await self.uow.commit()

        logger.info("assign_manager: node=%s manager=%s", node_id, manager_id)
        return node

    async def delete_subtree(self, node_id: UUID, current_user: CurrentUser) -> int:
        """Каскадно (мягко) удаляет подразделение вместе со всем его поддеревом.

        Использует ltree для поиска всех потомков одним запросом. Удаление мягкое —
        проставляется deleted_at, строки физически не удаляются.

        Args:
            node_id (UUID): id удаляемого подразделения.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            int: количество удалённых узлов, включая сам узел.

        Raises:
            NotAuthorizedError: если пользователь не администратор компании.
            StructAdmNotFoundError: если подразделение не найдено.
            CrossCompanyAccessError: если подразделение принадлежит другой компании.
        """
        self._require_admin(current_user)

        node = await self._get_owned_node(node_id, current_user)

        subtree = await self.uow.struct_adm.get_descendants(node.path, include_self=True)
        deleted_at = datetime.now()
        for item in subtree:
            item.deleted_at = deleted_at

        await self.uow.commit()

        logger.info("delete_subtree: node=%s deleted %d nodes", node_id, len(subtree))
        return len(subtree)

    async def get_tree(self, current_user: CurrentUser) -> list[StructAdm]:
        """Возвращает всю оргструктуру компании текущего пользователя.

        Args:
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            list[StructAdm]: все узлы компании, отсортированные по пути.
        """
        return await self.uow.struct_adm.get_by_company(current_user.company_id)

    async def get_subtree(self, node_id: UUID, current_user: CurrentUser) -> list[StructAdm]:
        """Возвращает поддерево указанного подразделения.

        Args:
            node_id (UUID): id корня искомого поддерева.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            list[StructAdm]: узлы поддерева, не включая сам узел.

        Raises:
            StructAdmNotFoundError: если подразделение не найдено.
            CrossCompanyAccessError: если подразделение принадлежит другой компании.
        """
        node = await self._get_owned_node(node_id, current_user)
        return await self.uow.struct_adm.get_descendants(node.path)

    def _require_admin(self, current_user: CurrentUser) -> None:
        """Проверяет, что пользователь — администратор компании.

        Args:
            current_user (CurrentUser): контекст текущего пользователя.

        Raises:
            NotAuthorizedError: если пользователь не администратор.
        """
        if not current_user.is_admin:
            logger.warning("access denied for user %s (role=%s)", current_user.user_id, current_user.role)
            raise NotAuthorizedError

    async def _get_owned_node(
        self,
        node_id: UUID,
        current_user: CurrentUser,
        not_found_error: type[StructAdmNotFoundError] = StructAdmNotFoundError,
    ) -> StructAdm:
        """Загружает узел и проверяет, что он принадлежит компании пользователя.

        Args:
            node_id (UUID): id подразделения.
            current_user (CurrentUser): контекст текущего пользователя.
            not_found_error (type[StructAdmNotFoundError]): класс исключения,
                выбрасываемого если узел не найден — позволяет вызывающему коду
                различать 'узел не найден' и 'родитель не найден'.

        Returns:
            StructAdm: найденный узел.

        Raises:
            StructAdmNotFoundError: если узел не найден или уже удалён.
            CrossCompanyAccessError: если узел принадлежит другой компании.
        """
        node = await self.uow.struct_adm.get_by_id(node_id)
        if node is None or node.deleted_at is not None:
            raise not_found_error
        if node.company_id != current_user.company_id:
            logger.warning("cross-company access attempt: user=%s node=%s", current_user.user_id, node_id)
            raise CrossCompanyAccessError
        return node
