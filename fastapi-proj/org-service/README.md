# org-service

Организационная структура компании: дерево подразделений, должности, руководители.

## Запуск

В составе всей системы: `docker compose up` из корня проекта.

Локально (требуется поднятый `org-db` и `kafka`):

```bash
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8002
uv run python -m app.inbox.run_consumer       # в отдельном терминале
uv run python -m app.outbox.run_publisher     # в отдельном терминале
uv run python -m app.saga.run_saga_consumer   # в отдельном терминале
```

## Переменные окружения

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `DB_HOST` | `localhost` | Хост Postgres |
| `DB_PORT` | `5433` | Порт Postgres (снаружи Docker) |
| `DB_NAME` | `org_db` | Имя базы |
| `DB_USER` | `postgres` | Пользователь |
| `DB_PASS` | — | Пароль |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Адрес брокера |
| `KAFKA_TOPIC` | `org-events` | Топик собственных событий |
| `KAFKA_CONSUMER_TOPIC` | `auth-events` | Топик, из которого читаются события |
| `KAFKA_CONSUMER_GROUP` | `org-service` | Consumer group |
| `KAFKA_SAGA_COMMANDS_TOPIC` | `saga-commands` | Топик команд саги |
| `KAFKA_SAGA_REPLIES_TOPIC` | `saga-replies` | Топик ответов саги |
| `JWT_SECRET` | — | Общий секрет подписи токенов |
| `JWT_ALGORITHM` | `HS256` | Алгоритм подписи |

Токены сервис только проверяет — выпускает их `auth-service`.

## Эндпоинты

Базовый префикс: `/org/api/v1`. Все требуют JWT; изменения доступны только роли `admin`.

### Подразделения

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/struct-adm/root` | Создаёт корневое подразделение |
| `POST` | `/struct-adm/child` | Создаёт дочернее подразделение |
| `GET` | `/struct-adm/` | Всё дерево компании |
| `GET` | `/struct-adm/{id}/subtree` | Поддерево узла, не включая сам узел |
| `PATCH` | `/struct-adm/{id}` | Переименование |
| `PUT` | `/struct-adm/{id}/manager` | Назначение руководителя |
| `DELETE` | `/struct-adm/{id}` | Каскадное удаление узла с поддеревом |

### Должности

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/positions/` | Создаёт должность |
| `GET` | `/positions/` | Должности компании |
| `PATCH` | `/positions/{id}` | Переименование |
| `DELETE` | `/positions/{id}` | Удаление вместе с привязками и назначениями |
| `POST` | `/positions/struct-adm/{struct_adm_id}` | Привязывает должность к подразделению |
| `DELETE` | `/positions/struct-adm/{struct_adm_id}/{position_id}` | Отвязывает |
| `GET` | `/positions/struct-adm/{struct_adm_id}` | Должности подразделения |
| `POST` | `/positions/{id}/users` | Назначает сотрудника на должность |
| `DELETE` | `/positions/{id}/users/{user_id}` | Снимает с должности |
| `GET` | `/positions/users/{user_id}` | Должности сотрудника |

## Иерархия на ltree

Дерево подразделений хранится в колонке `struct_adm.path` типа `ltree`.

Путь строится из технических меток: корень — `n_<hex id узла>`, потомок дописывает
свой сегмент через точку. Человекочитаемое название лежит отдельно в `name` — метки
`ltree` допускают только `[A-Za-z0-9_]`, поэтому названия отделов в путь не попадают.

Запросы поддерева и предков используют операторы `<@` и `@>`. Для них создан
GiST-индекс — он добавлен в миграцию вручную и объявлен в `__table_args__` модели,
чтобы автогенерация Alembic не пыталась его удалить.

Расширение `ltree` включается первой командой начальной миграции.

## Реплика данных

Сервис не обращается к базе `auth-service`. Таблицы `company` и `user` наполняются
из событий `company.created` и `employee.created` через Inbox-консьюмер. Реплика
минимальна: id, имя, фамилия, компания.

## Модель данных

| Таблица | Назначение |
|---|---|
| `struct_adm` | Узлы оргструктуры (`ltree`), руководитель |
| `position` | Должности компании |
| `struct_adm_position` | Какие должности есть в подразделении |
| `user_position` | Кто на какой должности |
| `company`, `user` | Реплики из auth-service |
| `outbox_message`, `inbox_message` | Транспорт событий |

## Тесты

```bash
uv run pytest -v
```