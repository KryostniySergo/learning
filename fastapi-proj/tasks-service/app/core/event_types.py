from enum import Enum


class EventType(str, Enum):
    """Каталог типов событий и команд, которые знает tasks-service."""

    # доменные события, на которые подписан сервис
    COMPANY_CREATED = "company.created"
    EMPLOYEE_CREATED = "employee.created"
    EMPLOYEE_UPDATED = "employee.updated"

    # собственные доменные события
    TASK_STATUS_CHANGED = "task.status_changed"

    # команды саги, которые исполняет сервис
    TASKS_CREATE_WELCOME_TASK = "tasks.create_welcome_task"

    # ответы, которые сервис публикует в saga-replies
    TASKS_WELCOME_TASK_CREATED = "tasks.welcome_task_created"
    TASKS_WELCOME_TASK_FAILED = "tasks.welcome_task_failed"
