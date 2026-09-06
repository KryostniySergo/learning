# tasks-service

Задачник: создание задач, участники, статусы.

## Запуск

В составе всей системы: `docker compose up` из корня проекта.

Локально (требуется поднятый `tasks-db` и `kafka`):

```bash
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8003
uv run python -m app.inbox.run_consumer       # в отдельном терминале
uv run python -m app.outbox.run_publisher     # в отдельном терминале
uv run python -m app.saga.run_saga_consumer   # в отдельном терминале
```

## Переменные окружения

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `DB_HOST` | `localhost` | Хост Postgres |
| `DB_PORT` | `5434` | Порт Postgres (снаружи Docker) |
| `DB_NAME` | `tasks_db` | Имя базы |
| `DB_USER` | `postgres` | Пользователь |
| `DB_PASS` | — | Пароль |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Адрес брокера |
| `KAFKA_TOPIC` | `tasks-events` | Топик собственных событий |
| `KAFKA_CONSUMER_TOPIC` | `auth-events` | Топик, из которого читаются события |
| `KAFKA_CONSUMER_GROUP` | `tasks-service` | Consumer group |
| `KAFKA_SAGA_COMMANDS_TOPIC` | `saga-commands` | Топик команд саги |
| `KAFKA_SAGA_REPLIES_TOPIC` | `saga-replies` | Топик ответов саги |
| `JWT_SECRET` | — | Общий секрет подписи токенов |
| `JWT_ALGORITHM` | `HS256` | Алгоритм подписи |

## Эндпоинты

Базовый префикс: `/tasks/api/v1`. Все требуют JWT.

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/tasks/` | Создаёт задачу; автор — текущий пользователь |
| `GET` | `/tasks/` | Задачи компании; фильтр `status`, пагинация `limit`/`offset` |
| `GET` | `/tasks/{id}` | Задача с наблюдателями и исполнителями |
| `PATCH` | `/tasks/{id}` | Изменяет поля задачи |
| `PUT` | `/tasks/{id}/status` | Меняет статус, публикует `task.status_changed` |
| `DELETE` | `/tasks/{id}` | Удаляет задачу с участниками |

## Права

Изменять и удалять задачу может её автор, ответственный или администратор компании.
Читать задачи может любой сотрудник компании. Задачи чужой компании возвращают `404`,
а не `403` — чтобы перебором id нельзя было выяснить, что существует у других.

## Статусы задачи

```
NEW ──▶ IN_PROGRESS ──▶ DONE
 │            │
 └────┬───────┘
      ▼
  CANCELLED
```

`DONE` и `CANCELLED` терминальны, возврат назад запрещён. Таблица допустимых
переходов объявлена в `app/models/task.py` рядом с самим enum, сервис сверяется
с ней при каждой смене статуса.

## Участники

| Поле | Тип | Хранение |
|---|---|---|
| Автор | один пользователь | `task.author_id` |
| Ответственный | один пользователь | `task.responsible_id` |
| Наблюдатели | список | таблица `task_watcher` |
| Исполнители | список | таблица `task_assignee` |

Все участники проверяются по локальной реплике: пользователь должен существовать
и состоять в той же компании, что и автор задачи. Если сотрудник ещё не приехал
из `auth-service` через Kafka, создание задачи вернёт `404`.

## Модель данных

| Таблица | Назначение |
|---|---|
| `task` | Задачи |
| `task_watcher`, `task_assignee` | Участники задачи |
| `company`, `user` | Реплики из auth-service |
| `outbox_message`, `inbox_message` | Транспорт событий |

## Тесты

```bash
uv run pytest -v
```