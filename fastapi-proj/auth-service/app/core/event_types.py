from enum import Enum


class EventType(str, Enum):
    """Каталог всех типов событий и команд, которые знает auth-service.

    Доменные события публикуются в auth-events, команды саги — в saga-commands,
    ответы исполнителей — в saga-replies.
    """

    # доменные события
    COMPANY_CREATED = "company.created"
    EMPLOYEE_CREATED = "employee.created"
    EMPLOYEE_REGISTERED = "employee.registered"

    # команды саги онбординга
    ORG_ASSIGN_EMPLOYEE = "org.assign_employee"
    ORG_UNASSIGN_EMPLOYEE = "org.unassign_employee"
    TASKS_CREATE_WELCOME_TASK = "tasks.create_welcome_task"
    AUTH_INVALIDATE_INVITE = "auth.invalidate_invite"

    # ответы исполнителей
    ORG_EMPLOYEE_ASSIGNED = "org.employee_assigned"
    ORG_EMPLOYEE_ASSIGNMENT_FAILED = "org.employee_assignment_failed"
    ORG_EMPLOYEE_UNASSIGNED = "org.employee_unassigned"
    TASKS_WELCOME_TASK_CREATED = "tasks.welcome_task_created"
    TASKS_WELCOME_TASK_FAILED = "tasks.welcome_task_failed"
    AUTH_INVITE_INVALIDATED = "auth.invite_invalidated"
