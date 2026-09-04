class NotAuthenticatedError(Exception):
    """Исключение, если запрос не содержит валидного токена."""


class NotAuthorizedError(Exception):
    """Исключение, если у пользователя недостаточно прав для операции."""


class TaskNotFoundError(Exception):
    """Исключение, если задача не найдена."""


class UserNotFoundError(Exception):
    """Исключение, если один из указанных пользователей отсутствует в реплике.

    Обычно означает, что событие employee.created ещё не обработано этим сервисом.
    """


class CrossCompanyAccessError(Exception):
    """Исключение при попытке обратиться к сущности другой компании."""


class InvalidStatusTransitionError(Exception):
    """Исключение при недопустимом переходе статуса задачи."""
