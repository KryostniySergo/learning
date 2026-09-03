class NotAuthorizedError(Exception):
    """Исключение, если у пользователя недостаточно прав для операции."""


class StructAdmNotFoundError(Exception):
    """Исключение, если подразделение не найдено."""


class ParentNotFoundError(StructAdmNotFoundError):
    """Исключение, если родительское подразделение не найдено."""


class PositionNotFoundError(Exception):
    """Исключение, если должность не найдена."""


class UserNotFoundError(Exception):
    """Исключение, если пользователь не найден в локальной реплике.

    Обычно означает, что событие employee.created от auth-service
    ещё не было обработано этим сервисом.
    """


class PositionAlreadyLinkedError(Exception):
    """Исключение, если должность уже привязана к этому подразделению."""


class PositionNotLinkedError(Exception):
    """Исключение, если должность не привязана к указанному подразделению."""


class UserAlreadyAssignedError(Exception):
    """Исключение, если сотрудник уже назначен на эту должность."""


class UserNotAssignedError(Exception):
    """Исключение, если сотрудник не назначен на указанную должность."""


class StructAdmHasChildrenError(Exception):
    """Исключение при попытке удалить подразделение, у которого есть дочерние."""


class CrossCompanyAccessError(Exception):
    """Исключение при попытке обратиться к сущности другой компании."""
