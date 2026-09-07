from enum import Enum


class EventType(str, Enum):
    """Каталог типов событий и команд, которые знает org-service.

    Значения должны совпадать с EventType в остальных сервисах — единый
    контракт поддерживается синхронизацией строковых значений.
    """

    # доменные события, на которые подписан сервис
    COMPANY_CREATED = "company.created"
    EMPLOYEE_CREATED = "employee.created"
    EMPLOYEE_UPDATED = "employee.updated"

    # команды саги, которые исполняет сервис
    ORG_ASSIGN_EMPLOYEE = "org.assign_employee"
    ORG_UNASSIGN_EMPLOYEE = "org.unassign_employee"

    # ответы, которые сервис публикует в saga-replies
    ORG_EMPLOYEE_ASSIGNED = "org.employee_assigned"
    ORG_EMPLOYEE_ASSIGNMENT_FAILED = "org.employee_assignment_failed"
    ORG_EMPLOYEE_UNASSIGNED = "org.employee_unassigned"
