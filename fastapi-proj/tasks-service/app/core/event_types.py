from enum import Enum


class EventType(str, Enum):
    """Каталог типов событий, которые публикует и слушает tasks-service.

    Значения должны совпадать с EventType в остальных сервисах — единый
    контракт событий поддерживается синхронизацией строковых значений.
    """

    COMPANY_CREATED = "company.created"
    EMPLOYEE_CREATED = "employee.created"
    TASK_STATUS_CHANGED = "task.status_changed"
