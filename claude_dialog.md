

# Контекст проекта для агента (сжатая сводка)

## Задание

Учебный pet-проект: микросервисная система управления бизнесом на FastAPI. Обязательные паттерны: Repository, Service Layer, Unit of Work, DI, DTO/Schema, Router Composition, Idempotency, Centralized Error Handling, Transactional Outbox, Idempotent Consumer/Inbox, Adapter/Gateway (Kafka), Saga/Orchestrator, Event Contracts.

3 микросервиса (у каждого своя БД Postgres, общаются через Kafka):

- **auth-service** — регистрация, аутентификация, личные данные (в активной разработке)
- **org-service** — оргструктура на PostgreSQL ltree (ещё не начат)
- **tasks-service** — задачник (ещё не начат)

Стек: Python 3.12+, FastAPI, SQLAlchemy 2.0 async, PostgreSQL, Kafka (aiokafka), Alembic, uv, Ruff.

## Архитектурные решения, принятые в диалоге

**Границы сервисов и реплики.** org-service и tasks-service хранят минимальную "реплику" пользователей у себя: `id, company, name, surname, created_at, deleted_at` (без email/пароля — это только у auth). Reasoning: сервисы не ходят в чужие БД, только через события.

**Таблица событий:**

| Событие | Публикует | Слушает | Payload |
|---|---|---|---|
| `company.created` | auth-service | org, tasks | company_id, name, created_at, deleted_at |
| `employee.created` | auth-service | org, tasks | employee_id, name, surname, company_id, created_at, deleted_at |
| `employee.registered` | auth-service | **только Saga-оркестратор** (не org/tasks напрямую!) | employee_id, name, surname, ... |
| `employee.email_changed` | — | — | **Решили не публиковать в Kafka вообще** — нет реального слушателя (email не входит ни в одну реплику) |

**Saga онбординга** (обязательна по заданию, оркестрация, не хореография): `employee.registered` → org-service привязывает к отделу → tasks-service создаёт приветственную задачу, с компенсацией при провале. Оркестратор — отдельный модуль `saga/` **внутри auth-service** (не отдельный 4-й сервис, для простоты старта), логически изолирован, общается со всеми сервисами (включая "родной" auth) только через команды/события, никогда напрямую не вызывает их сервисные слои. Команды/ответы саги — **в отдельных топиках Kafka**, не вместе с обычными доменными событиями (разное партиционирование по aggregate_id, разная семантика: событие vs команда). Хореография — только бонус, делается ПОСЛЕ обязательной оркестрации, как отдельная, независимая реализация (не переиспользует код саги).

**Envelope (обёртка событий):** `event_id` (UUID, для Inbox-дедупликации), `event_type` (строка, роутинг парсинга payload), `aggregate_id` (UUID, ключ партиционирования Kafka — гарантирует порядок событий одной сущности), `occurred_at`, `payload`, `schema_version`, `producer`. В БД `OutboxMessage` отдельными колонками: `id, event_id, event_type, aggregate_id, occurred_at, payload(JSONB), status, retry_count` — остальное (event_id как строка, schema_version, producer) кладётся ВНУТРЬ payload/envelope в JSONB.

**Outbox/Inbox паттерн:** Outbox — гарантия, что бизнес-изменение и запись о событии происходят в одной транзакции (защита от потери события при падении процесса). Inbox — гарантия идемпотентности на стороне консьюмера (проверка `event_id` в таблице `inbox_messages` ДО обработки, запись в inbox И бизнес-эффект — одна транзакция).

## Модели auth-service (все созданы, миграция применена в БД `auth_db`)

`app/models/base.py`: `Base(DeclarativeBase)` с автогенерацией `__tablename__` через `camel_to_snake(cls.__name__)`; `TimestampMixin` (created_at server_default=now(), deleted_at nullable) — подключается ОТДЕЛЬНО к моделям, где нужен.

- **Company**: id(UUID), name, +TimestampMixin
- **User**: id(UUID), name, surname, +TimestampMixin (НЕ хранит company_id напрямую!)
- **Member** (связь user↔company, many-to-many): id, user_id(FK), company_id(FK), role(enum ADMIN/USER), +TimestampMixin
- **Account**: id(UUID), email(unique, index), +TimestampMixin (НЕ хранит invite_id — направление связи обратное)
- **Invite**: id, token(unique, index), status(enum CREATED/IN_PROGRESS/COMPLETED/FAILED), expires_at(Python default = now+14 дней через функцию, НЕ server_default), user_id(FK, nullable=True — т.к. может не существовать на момент создания инвайта), account_id(FK, NOT NULL), +TimestampMixin
- **Secrets**: id, password_hash, user_id(FK, unique), account_id(FK, unique), +TimestampMixin — один пользователь = одна активная запись (update on password change, не история)
- **OutboxMessage**: id, event_id, event_type, aggregate_id, occurred_at(Python-side default=datetime.now), payload(JSONB), status(enum CREATED/SENT/FAILED), retry_count(default=0) — БЕЗ TimestampMixin (occurred_at покрывает эту роль)
- **InboxMessage**: id, event_id(unique), event_type, consumer_name, received_at, status(enum RECEIVED/PROCESSED/FAILED)

**НЕ создана `Credentials`/api_key** — осознанно пропущена, в задании упомянута, но ни один функциональный сценарий её не требует (только JWT).

**Важно:** UUID импортируется с алиасом `from uuid import UUID as PyUUID` в моделях, т.к. `Mapped[UUID]` конфликтует с SQL-типом `sqlalchemy.UUID`, если импортированы под одним именем (была реальная ошибка `MappedAnnotationError`).

**relationship() сознательно НЕ используется нигде** — только чистые FK-колонки (`user_id`, `company_id` и т.д.). Решение принято осознанно (YAGNI), но имеет цену — см. баги ниже.

## Инфраструктура (готова)

- `app/db/session.py` — async engine, `async_session_maker` с `expire_on_commit=False`, `autoflush=False`
- `app/uow.py` — `UnitOfWork` (async context manager), открывает сессию, создаёт все репозитории на ней, commit/rollback, логирование через `logging.getLogger`
- `app/repositories/base.py` — `BaseRepository[ModelType]` generic с `get_by_id`, `add`
- 7 конкретных репозиториев (Account, Company, User, Member, Invite, Secrets, Outbox), у Invite есть `get_by_token` и `get_by_account_id` (сортировка по created_at desc, последний инвайт)
- `app/core/config.py` — `Settings(BaseSettings)`: db_name, db_port, db_user, db_pass, db_host, **producer_name** (для outbox), `.database_url` property
- `app/core/logging.py` — `setup_logging()`, вызывается в main.py при старте
- `app/core/security.py` — `hash_password`/`verify_password` через bcrypt
- `app/core/exceptions.py` — доменные исключения: `AccountAlreadyExistsError`, `InviteNotFoundError`, `InviteExpiredError`, `InviteInvalidStatusError`, `InviteAccountMismatchError`
- `app/core/event_types.py` — `EventType(str, Enum)`: COMPANY_CREATED="company.created", EMPLOYEE_CREATED="employee.created", EMPLOYEE_REGISTERED="employee.registered" (единый источник правды вместо magic strings)
- `app/core/outbox.py` — `build_outbox_message(event_type: EventType, aggregate_id: UUID, payload: dict) -> OutboxMessage` — генерирует event_id и id объекта ЯВНО через uuid4() (не полагаясь на ORM default), собирает envelope, occurred_at через `datetime.now()` (Python-side, не server_default)

## Бизнес-логика — AuthService (app/services/auth_service.py)

Реализованы и протестированы все 3 шага регистрации компании:

1. **check_account(email)** — проверка занятости email, создание Account+Invite атомарно, защита от race condition через try/except IntegrityError → AccountAlreadyExistsError. Токен генерируется через `secrets.token_urlsafe(32)`.
2. **sign_up(email, invite_token)** — guard-переходы статуса: NotFound → AccountMismatch → Expired (помечает FAILED и коммитит) → InvalidStatus (если не CREATED) → переводит в IN_PROGRESS.
3. **sign_up_complete(email, password, first_name, last_name, company_name)** — создаёт Company, User(admin), Member(role=ADMIN — хардкод, т.к. это ВСЕГДА первый юзер новой компании; для обычных сотрудников будет ОТДЕЛЬНЫЙ метод), Secrets(hash_password), переводит Invite в COMPLETED, публикует 2 события в outbox (company.created, employee.created) через build_outbox_message. Возвращает (company_id, user_id).

Все методы принимают ПРИМИТИВЫ (str, UUID), не Pydantic-схемы — сервисный слой не должен знать о HTTP-контракте (schemas остаются на уровне эндпоинтов).

Эндпоинты в `app/api/v1/endpoints/auth.py`: GET check_account/{account} (account: EmailStr для валидации), POST sign-up/, POST sign-up-complete/. Все доменные исключения маппятся в HTTP через `raise HTTPException(...) from exc` (Ruff B904). check_account("not-an-email") теперь возвращает 422 благодаря EmailStr.

## Два реальных бага, которые уже словили и починили (важно для дальнейшей разработки!)

1. **`default=uuid4` в mapped_column вычисляется только при flush(), НЕ при создании объекта Python.** Из-за `autoflush=False` обращение к `obj.id` сразу после `Account(email=...)` возвращало `None`. **Решение-правило: ВСЕГДА передавать `id=uuid4()` явно в конструкторе**, если id нужен сразу же в той же транзакции для связанных объектов.

2. **Без relationship() SQLAlchemy не гарантирует порядок INSERT/UPDATE между разными таблицами, если одна операция ссылается на ещё не вставленный id другой.** Конкретно: `UPDATE invite SET user_id=...` может уйти в БД РАНЬШЕ `INSERT INTO user`, что дало `ForeignKeyViolationError`. **Решение-правило: `await self.uow.session.flush()` сразу после создания объекта, от чьего id зависят последующие insert/update других объектов** (flush нужно ставить СРАЗУ после проблемного объекта, а не в конце пачки операций — иначе flush просто отправит все pending-объекты в неправильном порядке той же проблемы).

Решение пока НЕ добавлять relationship() — осознанный выбор (YAGNI), пересмотреть если ручных flush() станет слишком много или понадобятся JOIN-запросы в репозиториях.

## Что дальше (следующий шаг)

**Outbox Publisher** — фоновый процесс, который читает `outbox_messages` со статусом CREATED, отправляет в Kafka через aiokafka (Adapter/Gateway паттерн — работа с Kafka спрятана за обёрткой), помечает SENT/FAILED, обрабатывает retry_count. Ещё не начат. После этого — org-service с нуля (аналогичная структура + Inbox-консьюмер + ltree для оргструктуры), затем tasks-service, затем Saga-оркестратор.

## Стиль работы с пользователем (важно для агента!)

Пользователь — учится, проект сдаёт как задание с ограниченным временем. **В начале диалога** обучение шло через сократовский метод (наводящие вопросы, без прямых ответов) — сейчас пользователь ПОПРОСИЛ ускориться: **писать код сразу**, короткие пояснения, без вороха уточняющих вопросов. Docstring — обязательны везде, Google-style (Args/Returns/Raises), даже для однострочных функций. Комментарии в коде — минимальные. Пользователь любит понимать "почему", уточняет архитектурные решения (не просто копирует код), стоит объяснять причины багов и решений кратко, но по существу.