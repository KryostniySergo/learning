class AccountAlreadyExistsError(Exception):
    """Исключение при попытке создать Account с уже занятой почтой (гонка запросов)."""


class InviteNotFoundError(Exception):
    """Исключение, если инвайт с таким токеном не найден."""


class InviteExpiredError(Exception):
    """Исключение, если срок действия инвайта истёк."""


class InviteInvalidStatusError(Exception):
    """Исключение, если инвайт не в том статусе, чтобы выполнить запрошенный переход."""


class InviteAccountMismatchError(Exception):
    """Исключение, если токен инвайта не соответствует указанной почте."""


class InvalidCredentialsError(Exception):
    """Исключение при неверной паре почта/пароль."""


class NotAuthenticatedError(Exception):
    """Исключение, если запрос не содержит валидного токена."""


class NotAuthorizedError(Exception):
    """Исключение, если у пользователя недостаточно прав для операции."""


class EmployeeAlreadyInCompanyError(Exception):
    """Исключение, если сотрудник уже состоит в этой компании."""


class CompanyNotFoundError(Exception):
    """Исключение, если компания не найдена."""
