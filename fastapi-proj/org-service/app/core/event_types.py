from enum import Enum


class EventType(str, Enum):
    """Каталог типов событий, которые обрабатывает org-service.

    Значения должны точно совпадать с EventType в auth-service — это разные
    файлы в разных сервисах (никакого общего пакета между ними), но единый
    контракт событий держится синхронизацией строковых значений.
    """

    COMPANY_CREATED = "company.created"
    EMPLOYEE_CREATED = "employee.created"
