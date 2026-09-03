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


class StructAdmHasChildrenError(Exception):
    """Исключение при попытке удалить подразделение, у которого есть дочерние."""


class CrossCompanyAccessError(Exception):
    """Исключение при попытке обратиться к сущности другой компании."""
