from enum import Enum


class EventType(str, Enum):
    """Единый источник правды для типов событий, публикуемых сервисом."""

    COMPANY_CREATED = "company.created"
    EMPLOYEE_CREATED = "employee.created"
    EMPLOYEE_REGISTERED = "employee.registered"
