import logging
from datetime import datetime
from uuid import UUID, uuid4

from app.core.exceptions import (
    CrossCompanyAccessError,
    NotAuthorizedError,
    PositionAlreadyLinkedError,
    PositionNotFoundError,
    PositionNotLinkedError,
    StructAdmNotFoundError,
    UserAlreadyAssignedError,
    UserNotAssignedError,
    UserNotFoundError,
)
from app.models.position import Position
from app.models.struct_adm import StructAdm
from app.models.struct_adm_position import StructAdmPosition
from app.models.user_position import UserPosition
from app.schemas.current_user import CurrentUser
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


class PositionService:
    """Бизнес-логика управления должностями и их привязками."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Инициализирует сервис.

        Args:
            uow (UnitOfWork): единица работы, дающая доступ к репозиториям и транзакции.
        """
        self.uow = uow

    async def create(self, title: str, current_user: CurrentUser) -> Position:
        """Создаёт должность в компании текущего пользователя.

        Args:
            title (str): название должности.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            Position: созданная должность.

        Raises:
            NotAuthorizedError: если пользователь не администратор компании.
        """
        self._require_admin(current_user)

        position = Position(id=uuid4(), title=title, company_id=current_user.company_id)
        self.uow.position.add(position)
        await self.uow.commit()

        logger.info("position created: %s (%s)", position.id, title)
        return position

    async def rename(self, position_id: UUID, title: str, current_user: CurrentUser) -> Position:
        """Переименовывает должность.

        Args:
            position_id (UUID): id должности.
            title (str): новое название.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            Position: обновлённая должность.

        Raises:
            NotAuthorizedError: если пользователь не администратор компании.
            PositionNotFoundError: если должность не найдена.
            CrossCompanyAccessError: если должность принадлежит другой компании.
        """
        self._require_admin(current_user)

        position = await self._get_owned_position(position_id, current_user)
        position.title = title
        await self.uow.commit()

        logger.info("position renamed: %s -> %s", position_id, title)
        return position

    async def delete(self, position_id: UUID, current_user: CurrentUser) -> None:
        """Мягко удаляет должность вместе со всеми её привязками.

        Снимает всех сотрудников с этой должности и отвязывает её от подразделений.

        Args:
            position_id (UUID): id должности.
            current_user (CurrentUser): контекст текущего пользователя.

        Raises:
            NotAuthorizedError: если пользователь не администратор компании.
            PositionNotFoundError: если должность не найдена.
            CrossCompanyAccessError: если должность принадлежит другой компании.
        """
        self._require_admin(current_user)

        position = await self._get_owned_position(position_id, current_user)
        deleted_at = datetime.now()

        assignments = await self.uow.user_position.get_by_position(position_id)
        for assignment in assignments:
            assignment.deleted_at = deleted_at

        links = await self.uow.struct_adm_position.get_by_position(position_id)
        for link in links:
            link.deleted_at = deleted_at

        position.deleted_at = deleted_at
        await self.uow.commit()

        logger.info(
            "position deleted: %s (released %d assignments, %d struct links)",
            position_id,
            len(assignments),
            len(links),
        )

    async def list_positions(self, current_user: CurrentUser) -> list[Position]:
        """Возвращает все должности компании текущего пользователя.

        Args:
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            list[Position]: должности компании.
        """
        return await self.uow.position.get_by_company(current_user.company_id)

    async def link_to_struct_adm(
        self, struct_adm_id: UUID, position_id: UUID, current_user: CurrentUser
    ) -> StructAdmPosition:
        """Привязывает должность к подразделению.

        Args:
            struct_adm_id (UUID): id подразделения.
            position_id (UUID): id должности.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            StructAdmPosition: созданная привязка.

        Raises:
            NotAuthorizedError: если пользователь не администратор компании.
            StructAdmNotFoundError: если подразделение не найдено.
            PositionNotFoundError: если должность не найдена.
            CrossCompanyAccessError: если сущности принадлежат другой компании.
            PositionAlreadyLinkedError: если должность уже привязана к подразделению.
        """
        self._require_admin(current_user)

        await self._get_owned_struct_adm(struct_adm_id, current_user)
        await self._get_owned_position(position_id, current_user)

        existing = await self.uow.struct_adm_position.get_link(struct_adm_id, position_id)
        if existing is not None:
            raise PositionAlreadyLinkedError

        link = StructAdmPosition(id=uuid4(), struct_adm_id=struct_adm_id, position_id=position_id)
        self.uow.struct_adm_position.add(link)
        await self.uow.commit()

        logger.info("position %s linked to struct_adm %s", position_id, struct_adm_id)
        return link

    async def unlink_from_struct_adm(self, struct_adm_id: UUID, position_id: UUID, current_user: CurrentUser) -> None:
        """Отвязывает должность от подразделения.

        Args:
            struct_adm_id (UUID): id подразделения.
            position_id (UUID): id должности.
            current_user (CurrentUser): контекст текущего пользователя.

        Raises:
            NotAuthorizedError: если пользователь не администратор компании.
            StructAdmNotFoundError: если подразделение не найдено.
            CrossCompanyAccessError: если подразделение принадлежит другой компании.
            PositionNotLinkedError: если должность не привязана к подразделению.
        """
        self._require_admin(current_user)

        await self._get_owned_struct_adm(struct_adm_id, current_user)

        link = await self.uow.struct_adm_position.get_link(struct_adm_id, position_id)
        if link is None:
            raise PositionNotLinkedError

        link.deleted_at = datetime.now()
        await self.uow.commit()

        logger.info("position %s unlinked from struct_adm %s", position_id, struct_adm_id)

    async def list_struct_adm_positions(
        self, struct_adm_id: UUID, current_user: CurrentUser
    ) -> list[StructAdmPosition]:
        """Возвращает должности, привязанные к подразделению.

        Args:
            struct_adm_id (UUID): id подразделения.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            list[StructAdmPosition]: привязки подразделение-должность.

        Raises:
            StructAdmNotFoundError: если подразделение не найдено.
            CrossCompanyAccessError: если подразделение принадлежит другой компании.
        """
        await self._get_owned_struct_adm(struct_adm_id, current_user)
        return await self.uow.struct_adm_position.get_by_struct_adm(struct_adm_id)

    async def assign_user(self, user_id: UUID, position_id: UUID, current_user: CurrentUser) -> UserPosition:
        """Назначает сотрудника на должность.

        Args:
            user_id (UUID): id сотрудника.
            position_id (UUID): id должности.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            UserPosition: созданное назначение.

        Raises:
            NotAuthorizedError: если пользователь не администратор компании.
            UserNotFoundError: если сотрудник отсутствует в локальной реплике.
            PositionNotFoundError: если должность не найдена.
            CrossCompanyAccessError: если сущности принадлежат другой компании.
            UserAlreadyAssignedError: если сотрудник уже назначен на эту должность.
        """
        self._require_admin(current_user)

        await self._get_owned_user(user_id, current_user)
        await self._get_owned_position(position_id, current_user)

        existing = await self.uow.user_position.get_link(user_id, position_id)
        if existing is not None:
            raise UserAlreadyAssignedError

        assignment = UserPosition(id=uuid4(), user_id=user_id, position_id=position_id)
        self.uow.user_position.add(assignment)
        await self.uow.commit()

        logger.info("user %s assigned to position %s", user_id, position_id)
        return assignment

    async def unassign_user(self, user_id: UUID, position_id: UUID, current_user: CurrentUser) -> None:
        """Снимает сотрудника с должности.

        Args:
            user_id (UUID): id сотрудника.
            position_id (UUID): id должности.
            current_user (CurrentUser): контекст текущего пользователя.

        Raises:
            NotAuthorizedError: если пользователь не администратор компании.
            UserNotFoundError: если сотрудник отсутствует в локальной реплике.
            CrossCompanyAccessError: если сотрудник из другой компании.
            UserNotAssignedError: если сотрудник не назначен на эту должность.
        """
        self._require_admin(current_user)

        await self._get_owned_user(user_id, current_user)

        assignment = await self.uow.user_position.get_link(user_id, position_id)
        if assignment is None:
            raise UserNotAssignedError

        assignment.deleted_at = datetime.now()
        await self.uow.commit()

        logger.info("user %s unassigned from position %s", user_id, position_id)

    async def list_user_positions(self, user_id: UUID, current_user: CurrentUser) -> list[UserPosition]:
        """Возвращает должности, занимаемые сотрудником.

        Args:
            user_id (UUID): id сотрудника.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            list[UserPosition]: назначения сотрудника.

        Raises:
            UserNotFoundError: если сотрудник отсутствует в локальной реплике.
            CrossCompanyAccessError: если сотрудник из другой компании.
        """
        await self._get_owned_user(user_id, current_user)
        return await self.uow.user_position.get_by_user(user_id)

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

    async def _get_owned_position(self, position_id: UUID, current_user: CurrentUser) -> Position:
        """Загружает должность и проверяет принадлежность компании пользователя.

        Args:
            position_id (UUID): id должности.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            Position: найденная должность.

        Raises:
            PositionNotFoundError: если должность не найдена или удалена.
            CrossCompanyAccessError: если должность принадлежит другой компании.
        """
        position = await self.uow.position.get_by_id(position_id)
        if position is None or position.deleted_at is not None:
            raise PositionNotFoundError
        if position.company_id != current_user.company_id:
            raise CrossCompanyAccessError
        return position

    async def _get_owned_struct_adm(self, struct_adm_id: UUID, current_user: CurrentUser) -> StructAdm:
        """Загружает подразделение и проверяет принадлежность компании пользователя.

        Args:
            struct_adm_id (UUID): id подразделения.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            StructAdm: найденный узел.

        Raises:
            StructAdmNotFoundError: если подразделение не найдено или удалено.
            CrossCompanyAccessError: если подразделение принадлежит другой компании.
        """
        node = await self.uow.struct_adm.get_by_id(struct_adm_id)
        if node is None or node.deleted_at is not None:
            raise StructAdmNotFoundError
        if node.company_id != current_user.company_id:
            raise CrossCompanyAccessError
        return node

    async def _get_owned_user(self, user_id: UUID, current_user: CurrentUser):
        """Загружает сотрудника из реплики и проверяет принадлежность компании.

        Args:
            user_id (UUID): id сотрудника.
            current_user (CurrentUser): контекст текущего пользователя.

        Returns:
            User: найденный сотрудник.

        Raises:
            UserNotFoundError: если сотрудник отсутствует в локальной реплике.
            CrossCompanyAccessError: если сотрудник из другой компании.
        """
        user = await self.uow.user.get_by_id(user_id)
        if user is None or user.deleted_at is not None:
            raise UserNotFoundError
        if user.company_id != current_user.company_id:
            raise CrossCompanyAccessError
        return user
