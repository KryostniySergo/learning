# Паттерны программирования

Разбор паттернов проектирования, типичных для современного бэкенда на Python
(FastAPI + SQLAlchemy + Kafka). Для каждого паттерна: **что это**, **пример
кода**, **как работает** и **зачем** (какую проблему решает и какова цена).

Все примеры абстрактные и самодостаточные — это обобщённые шаблоны, а не код
конкретного проекта.

## Содержание

**Слой данных и бизнес-логики**
1. Repository (Репозиторий)
2. Service Layer (Сервисный слой)
3. Unit of Work (Единица работы)

**Сборка приложения**

4. Dependency Injection (Внедрение зависимостей)
5. DTO / Schema (Контракты данных)

**Веб-слой (FastAPI)**

6. Router Composition (Композиция роутеров и версионирование)
7. Dependency Injection для сквозных задач
8. Idempotency (Идемпотентность)
9. Centralized Error Handling (Обработка ошибок)

**Событийно-ориентированная архитектура (Kafka)**

10. Transactional Outbox (Транзакционный outbox)
11. Idempotent Consumer / Inbox
12. Adapter / Gateway (обёртка над брокером)
13. Saga / Orchestrator (Оркестратор и компенсации)
14. Event Contracts (Контракты событий)

---

## 1. Repository (Репозиторий)

**Что это.** Паттерн, который прячет детали доступа к данным (SQL, ORM) за
объектным интерфейсом. Бизнес-логика работает с «коллекцией объектов», а не с
запросами.

**Пример.**

```python
from sqlalchemy import Select, insert, select

class BaseRepo[PK, Model]:
    def __init__(self, model: type[Model]) -> None:
        self.model = model

    def create(self, data: dict) -> Select:
        return insert(self.model).values(**data).returning(self.model)

    def retrieve(self, entity_id: PK) -> Select:
        return select(self.model).where(self.model.id == entity_id).limit(1)

class UserRepo(BaseRepo[int, User]):
    def retrieve_by_email(self, email: str) -> Select:
        # доменный запрос строится поверх базового select
        return select(self.model).where(self.model.email == email)
```

**Как работает.** Полезный приём — методы репозитория **возвращают объект
запроса (`Select`), а не выполняют его**. Выполнением (`await session.execute`)
занимается сервисный слой. Это делает запросы композируемыми: на возвращённый
`Select` можно навесить дополнительные фильтры, сортировки, `options`. Базовый
класс даёт стандартные CRUD, чтобы не дублировать их в каждом репозитории.

**Зачем.**
- **Изоляция SQL.** Поменялась схема или способ выборки — правки локализованы.
- **Тестируемость.** Репозиторий легко подменить тестовым двойником.
- **Единый словарь запросов.** Доменные имена (`retrieve_by_email`) вместо
ad-hoc SQL в разных местах.

**Цена.** Лишний слой абстракции; для тривиальных выборок выглядит избыточно.
Окупается на большом кодовой базе.

---

## 2. Service Layer (Сервисный слой)

**Что это.** Слой, где живёт бизнес-логика и сценарии. Сервис оркестрирует
несколько репозиториев и других сервисов, применяет правила и обозначает
границы транзакции. Контроллеры (вьюхи) остаются тонкими.

**Пример.**

```python
class OrderService:
    def __init__(
        self,
        order_repo: OrderRepo,
        inventory_service: InventoryService,
        pricing_service: PricingService,
    ) -> None:
        self.order_repo = order_repo
        self.inventory_service = inventory_service
        self.pricing_service = pricing_service

    async def place_order(self, session: AsyncSession, data: CreateOrderDTO) -> Order:
        # 1. бизнес-правила
        await self.inventory_service.ensure_available(session, data.items)
        total = await self.pricing_service.calculate_total(session, data.items)

        # 2. создание основной сущности
        order = await session.scalar(self.order_repo.create({**data.dict(), "total": total}))

        # 3. связанные изменения — всё в той же сессии
        await self.inventory_service.reserve(session, order.id, data.items)
        return order
```

**Как работает.** Каждый публичный метод принимает `session` первым аргументом
— сессия «прокидывается» сверху (из вьюхи) через весь стек. Сервис **сам не
коммитит** транзакцию (этим занимается Unit of Work, см. §3) — он лишь описывает,
*что* должно произойти атомарно. Зависимости приходят в конструктор (инъекция,
см. §4).

**Зачем.**
- **Разделение ответственности.** Вьюха = HTTP, сервис = правила, репозиторий = SQL.
- **Переиспользование.** Тот же сервис вызывают и API, и воркер, и консьюмер.
- **Транзакционная целостность.** Все шаги — на одной сессии → один коммит.

---

## 3. Unit of Work (Единица работы)

**Что это.** Паттерн, удерживающий набор изменений в одной транзакции и
коммитящий/откатывающий их атомарно. Часто реализуется не явным объектом
`UnitOfWork`, а связкой **middleware (сессия на запрос)** + **декоратор границ
транзакции** + **post-commit hooks**.

**Пример.** Сессия — одна на запрос:

```python
class DBSessionMiddleware:
    def __init__(self, app, session_factory):
        self.app = app
        self.session_factory = session_factory

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            scope["db_session"] = self.session_factory()
            try:
                await self.app(scope, receive, send)
            finally:
                session = scope.pop("db_session", None)
                if session is not None:
                    await session.close()
            return
        await self.app(scope, receive, send)
```

Границы транзакции — декоратор поверх обработчика:

```python
def managed_db_session(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        session = kwargs["db_session"]
        try:
            result = await func(*args, **kwargs)
            await session.commit()          # успех → коммит
        except Exception:
            await session.rollback()        # ошибка → откат
            raise
        else:
            await PostCommitHooks.drain(session)  # эффекты ПОСЛЕ коммита
            return result
    return wrapper
```

Post-commit hooks — побочные эффекты, которые должны произойти только при
успешном коммите:

```python
class PostCommitHooks:
    _KEY = "_post_commit_hooks"

    @staticmethod
    def register(session, callback):
        session.info.setdefault(PostCommitHooks._KEY, []).append(callback)

    @staticmethod
    async def drain(session):
        hooks = session.info.pop(PostCommitHooks._KEY, [])
        results = await asyncio.gather(*[h() for h in hooks], return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.error("post-commit hook failed:%s", result)
```

**Как работает.** Middleware кладёт сессию в scope запроса → вьюха достаёт её
→ сервисы пишут изменения → декоратор на выходе делает `commit` (или `rollback`
при исключении) → затем `drain` выполняет отложенные эффекты. Важный инвариант
надёжных систем: **смена бизнес-состояния и запись события в outbox происходят
в одной транзакции** (см. §10).

**Зачем.**
- **Атомарность сценария.** Одна чёткая граница транзакции, а не разбросанные
по сервисам коммиты.
- **Безопасность от частичных записей.** Любое исключение → полный откат.
- **Корректные побочные эффекты.** Hooks не выстрелят при откате.

---

## 4. Dependency Injection (Внедрение зависимостей)

**Что это.** Объекты не создают свои зависимости сами, а получают их извне. На
практике — декларативный контейнер, описывающий граф объектов в одном месте
(в примере — библиотека `that_depends`).

**Пример.**

```python
from that_depends import BaseContainer, providers

class AppContainer(BaseContainer):
    # Singleton — один экземпляр на всё приложение (конфиг, движок БД)
    settings = providers.Singleton(Settings)
    db_engine = providers.Singleton(create_async_engine, url=settings.DB_DSN)
    session_factory = providers.Singleton(async_sessionmaker, db_engine.cast)

    # Factory — новый экземпляр на каждый вызов (stateless-сервисы/репозитории)
    order_repo = providers.Factory(OrderRepo, model=Order)
    order_service = providers.Factory(OrderService, order_repo=order_repo.cast)

    # Resource — асинхронный setup/teardown (клиенты, продюсеры)
    kafka_producer = providers.Resource(kafka_producer_resource, servers=settings.KAFKA)
```

Три типичных типа провайдеров:

| Провайдер | Жизненный цикл | Для чего |
| --- | --- | --- |
| `Singleton` | один на приложение | конфиг, движок БД, пулы |
| `Factory` | новый на каждый запрос | сервисы, репозитории (stateless) |
| `Resource` | async setup/teardown | HTTP-клиенты, брокер, S3 |

В тестах провайдер подменяется одной строкой:

```python
AppContainer.payment_gateway.override_sync(FakeGateway())
...
AppContainer.payment_gateway.reset_override_sync()
```

**Как работает.** Провайдеры ссылаются друг на друга (`order_repo.cast`),
образуя граф. При резолве контейнер строит объект и все его зависимости. Для
веб-фреймворка обычно есть интеграция, подключающая резолвинг к роутам.

**Зачем.**
- **Слабая связанность.** Сервис зависит от интерфейсов, а не от способа сборки.
- **Единый источник правды** для графа объектов.
- **Тестируемость.** Подмена реальных клиентов на фейки одной строкой.
- **Специализация.** Разным приложениям — разные подмножества контейнера.

---

## 5. DTO / Schema (Контракты данных)

**Что это.** Pydantic-модели, отделяющие контракт API (вход/выход) от доменных
ORM-моделей. Request- и response-схемы разнесены.

**Пример.**

```python
class CreateOrderRequestSchema(BaseModel):
    items: list[OrderItemSchema] = Field(min_length=1)
    coupon_code: str | None = Field(default=None, max_length=32)

class OrderResponseSchema(BaseModel):
    id: UUID
    status: OrderStatus
    total: Decimal
    created_at: datetime
```

**Конвенция именования.** Давайте схемам доменный префикс
(`OrderCreateRequestSchema`, а не безликий `CreateRequestSchema`) — при
кросс-доменных импортах сразу видно, откуда схема. Общие поля выносите в
миксины.

**Как работает.** На входе фреймворк валидирует тело запроса в `*RequestSchema`
(ограничения `Field`, паттерны, длины). На выходе сервис сериализует доменный
объект в `*ResponseSchema` (`Schema.model_validate(obj)`). ORM-модель наружу не
утекает.

**Зачем.**
- **Безопасность контракта.** Клиент не пришлёт лишних полей; ответ не «течёт»
внутренними полями БД.
- **Версионируемость.** Изменить ответ можно, не трогая модель БД.
- **Самодокументирование.** Эти же схемы рождают OpenAPI.

---

## 6. Router Composition (Композиция роутеров)

**Что это.** Вместо одного гигантского приложения — иерархическая сборка
независимых доменных роутеров. Версионирование решается префиксами/вложением.

**Пример.**

```python
# каждый домен владеет своим роутером, префиксом и тегами
orders_router = APIRouter(prefix="/orders", tags=["Orders"])
users_router = APIRouter(prefix="/users", tags=["Users"])

# корневой роутер агрегирует доменные
root = APIRouter()
root.include_router(orders_router)
root.include_router(users_router)

# версионирование — через вложение
api_v1 = APIRouter(prefix="/v1")
api_v1.include_router(root)

app.include_router(api_v1)
```

**Как работает.** Корневой роутер собирает доменные. У каждого — свой `prefix`
и `tags`. Кастомный `route_class` (если используется DI-интеграция) подключает
резолвинг ко всем вложенным роутерам сразу.

**Зачем.**
- **Модульность.** Каждый домен эволюционирует независимо.
- **Масштаб.** Добавить домен = одна строка `include_router`.
- **Управляемое версионирование.** Новую версию вводят новым префиксом, не
ломая старую.

---

## 7. FastAPI `Depends` для сквозных задач

**Что это.** Сквозные задачи (аутентификация, сессия БД, пагинация,
авторизация, выбор реализации сервиса) оформлены как переиспользуемые
зависимости через `Annotated[T, Depends(...)]`.

**Пример.**

```python
def get_db_session(request: Request) -> AsyncSession:
    return request.scope["db_session"]

class Pagination(BaseModel):
    limit: int = Query(20, ge=1, le=50)
    offset: int = Query(0, ge=0)

def get_current_user(
    token: Annotated[str, Depends(bearer_scheme)],
    jwt_service: Annotated[JWTService, Depends(AppContainer.jwt_service)],
) -> User:
    return jwt_service.decode(token)

@router.get("/orders/")
@managed_db_session
async def list_orders(
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    pages: Annotated[Pagination, Depends()],
    service: Annotated[OrderService, Depends(AppContainer.order_service)],
) -> PaginatedResponse[OrderResponseSchema]:
    ...
```

Полезный приём — **выбор реализации сервиса в рантайме** (например, по роли
пользователя), обёрнутый в зависимость-фабрику:

```python
def choose_serviceT:
    def _dep(
        user: Annotated[User, Depends(get_current_user)],
        impls: Annotated[dict[Role, T], Depends(factory)],
    ) -> T:
        return impls[user.role]
    return _dep
```

**Как работает.** Фреймворк рекурсивно резолвит дерево зависимостей до вызова
обработчика. Зависимости композируются (`get_current_user` используется внутри
других). Тип в `Annotated` даёт типобезопасность и автодополнение.

**Зачем.**
- **DRY.** Auth/пагинация/сессия пишутся один раз.
- **Тестируемость.** Любую зависимость можно переопределить.
- **Полиморфизм без if-ов в обработчике.**

---

## 8. Idempotency (Идемпотентность)

**Что это.** Гарантия, что повтор одного и того же запроса (сетевой ретрай,
двойной клик) не выполнит операцию дважды. Критично для платежей и любых
небезопасно-повторяемых операций.

**Пример.**

```python
async def process_idempotency_key(
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[UUID, Header()],
    request: Request,
    service: Annotated[IdempotencyService, Depends(AppContainer.idempotency_service)],
) -> UUID:
    body = await request.body()
    record = await service.get_or_create(
        db_session,
        key=idempotency_key,
        method=request.method,
        path=request.url.path,
        body=body,
    )
    if record.status == "FINISHED":
        # запрос уже завершён → отдаём сохранённый ответ, не выполняя снова
        raise IdempotencyRetry(status_code=record.response_code, content=record.response_body)
    return record.id

@router.post("/payments/")
@managed_db_session
async def create_payment(
    idempotency_key_id: Annotated[UUID, Depends(process_idempotency_key)],
    ...
) -> PaymentResponseSchema:
    ...
```

**Как работает.** Клиент шлёт заголовок `Idempotency-Key: <uuid>`. Сервис
делает `get_or_create` записи с фингерпринтом запроса (метод+путь+тело) и полем
статуса:
- ключ уже `FINISHED` → возвращаем **сохранённый прошлый ответ**;
- тело не совпало при том же ключе → `409 Conflict`;
- запрос ещё «в работе» → `423 Locked` (защита от гонки параллельных ретраев).

**Зачем.** Двойное списание недопустимо. Идемпотентный ключ превращает
«at-least-once»-доставку клиента в «effectively-once»-эффект на сервере.

---

## 9. Centralized Error Handling

**Что это.** Доменные исключения бросаются глубоко в бизнес-логике, а маппинг
«исключение → HTTP-статус» вынесен в один реестр. Бизнес-код ничего не знает об
HTTP.

**Пример.**

```python
# доменные исключения — без упоминания HTTP
class InsufficientBalanceError(Exception): ...
class NotFoundError(Exception): ...
class AuthorizationError(Exception): ...

def base_handler(status: HTTPStatus):
    async def _handler(request: Request, exc: Exception) -> JSONResponse:
        detail = exc.args[0] if exc.args else status.phrase
        return JSONResponse(status_code=status, content={"detail": detail})
    return _handler

# реестр маппинга
exception_handlers = {
    NotFoundError:           base_handler(HTTPStatus.NOT_FOUND),
    AuthorizationError:      base_handler(HTTPStatus.FORBIDDEN),
    InsufficientBalanceError: base_handler(HTTPStatus.BAD_REQUEST),
    IdempotencyRetry:        idempotency_handler,   # особый случай
}

app = FastAPI(exception_handlers=exception_handlers)
```

**Как работает.** Сервис бросает `InsufficientBalanceError` — фреймворк ловит
его по типу и вызывает соответствующий обработчик, формирующий JSON с нужным
кодом. Особые случаи получают свои обработчики (например, с дополнительным
логированием/метриками).

**Зачем.**
- **Чистота слоёв.** Бизнес-логика не импортирует HTTP-статусы.
- **Единообразие ответов об ошибках.**
- **Лёгкое расширение.** Новая ошибка = одна строка в реестре.

---

## 10. Transactional Outbox

**Что это.** Паттерн надёжной публикации событий. Вместо «записать в БД, потом
отправить в брокер» (где между шагами можно упасть и потерять сообщение)
событие пишется **в outbox-таблицу в той же транзакции**, что и бизнес-изменение.
Отдельный процесс потом публикует его в брокер.

**Пример.** Таблица outbox:

```python
class OutboxMessage(Base):
    event_id: Mapped[UUID] = mapped_column(unique=True)
    dedup_key: Mapped[str] = mapped_column(unique=True)
    event_type: Mapped[str]
    payload: Mapped[dict] = mapped_column(JSONB)
    available_at: Mapped[datetime]
    published_at: Mapped[datetime | None]
    attempts: Mapped[int] = mapped_column(server_default="0")
```

Запись события — в той же сессии, что и бизнес-логика:

```python
async def append_event(session, *, event_type, aggregate_id, payload, dedup_key):
    stmt = (
        insert(OutboxMessage)
        .values(event_id=uuid4(), dedup_key=dedup_key, event_type=event_type, payload=payload)
        .on_conflict_do_nothing(index_elements=["dedup_key"])  # идемпотентная вставка
        .returning(OutboxMessage)
    )
    return (await session.execute(stmt)).scalar_one_or_none()
```

Отдельный публикатор опрашивает таблицу и шлёт в брокер с backoff:

```python
async with kafka_producer(servers=..., acks="all") as producer:
    while not stop_event.is_set():
        async with session_factory() as session, session.begin():
            batch = await fetch_unpublished(session, limit=100)
            for msg in batch:
                try:
                    await producer.send_and_wait(topic, serialize(msg))
                    msg.published_at = now()
                except Exception as exc:
                    msg.attempts += 1
                    msg.available_at = now() + backoff(msg.attempts)  # ретрай позже
        if not batch:
            await asyncio.sleep(POLL_INTERVAL)
```

**Как работает.** `append_event` вызывается внутри бизнес-транзакции (та же
`session`). Коммит атомарно сохраняет и изменение, и событие. Если приложение
упадёт сразу после коммита — событие никуда не делось, публикатор подхватит его
позже. `on_conflict_do_nothing` по `dedup_key` не даёт создать дубль.

**Зачем.**
- **Нет потери сообщений.** Событие и бизнес-изменение коммитятся вместе.
- **Нет «фантомных» событий.** Откат транзакции → события нет.
- **Устойчивость к сбоям брокера.** Outbox копит, публикатор досылает.

---

## 11. Idempotent Consumer / Inbox

**Что это.** Зеркало outbox на стороне потребителя. Брокер гарантирует
«at-least-once» — одно сообщение может прийти повторно. Inbox-таблица с
уникальным ключом `(consumer_name, event_id)` гарантирует обработку **не более
одного раза**.

**Пример.** Таблица inbox:

```python
class InboxMessage(Base):
    consumer_name: Mapped[str]
    event_id: Mapped[UUID]
    status: Mapped[str] = mapped_column(server_default="PROCESSING")
    attempts: Mapped[int] = mapped_column(server_default="0")

    __table_args__ = (UniqueConstraint("consumer_name", "event_id"),)  # ключ дедупликации
```

Контекст-менеджер обработки:

```python
@asynccontextmanager
async def consume_event(session, *, consumer_name, event, max_retries=5):
    async with session.begin():
        slot = await acquire_slot(session, consumer_name, event.event_id, max_retries)
        if not slot.should_process:          # дубликат или исчерпаны ретраи
            if slot.exhausted:
                await park_to_dlq(session, event)   # dead-letter queue
            yield ConsumeContext(should_process=False)
            return

        nested = await session.begin_nested()
        try:
            yield ConsumeContext(should_process=True)   # тут работает бизнес-логика
        except Exception:
            await nested.rollback()
            attempts = await mark_failed(session, slot.inbox_id)
            if attempts >= max_retries:
                await park_to_dlq(session, event)
            raise
        else:
            await nested.commit()
            await mark_success(session, slot.inbox_id)
```

**Как работает.** Перед обработкой консьюмер пытается «занять слот» по
`(consumer_name, event_id)`. Уже есть строка — это дубль, обработка
пропускается. Бизнес-логика идёт во вложенной транзакции (`begin_nested`):
успех → `mark_success` + commit; ошибка → rollback + инкремент `attempts`, а
после исчерпания ретраев — «парковка» в DLQ. Важный инвариант: offset в брокере
коммитится **только после успеха** БД-транзакции, а проваленная обработка
никогда не помечается успехом.

**Зачем.**
- **Эффективно exactly-once.** Дубликаты брокера не приводят к повторным
эффектам.
- **Управляемые сбои.** Ретраи с лимитом + DLQ вместо бесконечного цикла.

---

## 12. Adapter / Gateway (обёртка над брокером)

**Что это.** Детали клиента брокера (запуск/остановка, acks, offset-семантика)
спрятаны за тонкими контекстными менеджерами. Остальной код не знает о
конкретной библиотеке.

**Пример.**

```python
@asynccontextmanager
async def kafka_producer(*, servers, acks="all"):
    producer = AIOKafkaProducer(bootstrap_servers=servers, acks=acks)
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()

@asynccontextmanager
async def kafka_consumer(*, topic, servers, group_id, auto_offset_reset="earliest"):
    consumer = AIOKafkaConsumer(topic, bootstrap_servers=servers,
                                group_id=group_id, auto_offset_reset=auto_offset_reset)
    await consumer.start()
    try:
        yield consumer
    finally:
        await consumer.stop()
```

**Как работает.** Везде, где нужен продюсер/консьюмер, используется
`async with kafka_producer(...) as producer`. Запуск/остановка и единые
настройки (`acks="all"`) гарантированы контекстным менеджером. Эту же обёртку
удобно завернуть в DI-провайдер `Resource` (см. §4).

**Зачем.**
- **Одна точка настройки** acks/offset/ретраев.
- **Гарантированная очистка** ресурсов даже при исключении.
- **Замена реализации** не затрагивает бизнес-код.

---

## 13. Saga / Orchestrator

**Что это.** Длинный распределённый бизнес-процесс проходит много шагов в разных
сервисах. Оркестратор — единая «машина состояний», которая принимает
команды-события, проверяет допустимость перехода и при сбое запускает
**компенсацию** (откат уже сделанных шагов). Альтернатива — хореография (каждый
сервис сам реагирует на события); оркестрация даёт единый контроль.

**Пример.** Диспетчер команд (роутер по типу события):

```python
async def dispatch_command(self, session, envelope: EventEnvelope) -> DispatchResult:
    match envelope.event_type:
        case "order.payment_confirmed":
            return await self._handle_payment_confirmed(session, envelope)
        case "order.cancel_requested":
            return await self._handle_cancel_requested(session, envelope)
        case "order.provider_failed":
            return await self._handle_provider_failed(session, envelope)
        case _:
            return DispatchResult(handled=False, reason="unknown_command")
```

Защита переходов (guard) — нельзя отменить то, что уже в финальном статусе:

```python
async def _handle_cancel_requested(self, session, envelope) -> DispatchResult:
    order = await self.repo.get(session, envelope.aggregate_id)
    cancellable = {OrderStatus.DRAFT, OrderStatus.PENDING, OrderStatus.PROCESSING}
    if order.status not in cancellable:
        return DispatchResult(handled=True, reason="wrong_status")   # переход запрещён
    await self._cancel(session, order)
    return DispatchResult(handled=True)
```

Компенсация — откат при провале (возврат денег и т.п.), атомарно вместе с
записью события в outbox:

```python
async def _handle_provider_failed(self, session, envelope) -> DispatchResult:
    order = await self.repo.get(session, envelope.aggregate_id)
    if order.status != OrderStatus.PENDING:
        return DispatchResult(handled=True, reason="wrong_status")
    # компенсация: точный обратный эффект ранее сделанного списания
    await self.balance_service.refund(session, order.payer_id, order.amount)
    await self.repo.set_status(session, order.id, OrderStatus.CANCELED)
    await append_event(session, event_type="order.canceled",
                       aggregate_id=str(order.id), payload={...}, dedup_key=...)
    return DispatchResult(handled=True)
```

**Как работает.** Команды приходят как события в брокер. `dispatch_command`
маршрутизирует по `event_type`. Каждый хендлер сначала проверяет текущий статус
(guard), затем выполняет переход **в одной транзакции** вместе с записью нового
события в outbox. Партиционирование по идентификатору агрегата даёт порядок
событий по каждой сущности. При провале — переход в компенсацию (точный
обратный эффект).

**Зачем.**
- **Нет распределённой транзакции** на несколько сервисов — её заменяет цепочка
событий + компенсации.
- **Один контроль состояния.** Все переходы — через один сервис, гонок меньше.
- **Корректность.** Компенсация — точный обратный эффект прежнего шага.

---

## 14. Event Contracts (Контракты событий)

**Что это.** Типы событий, их полезная нагрузка (payload) и «конверт»
(envelope) зафиксированы как версионируемые контракты — договор между
продюсерами и консьюмерами.

**Пример.** Типы событий — единый источник правды:

```python
class EventTypes(StrEnum):
    ORDER_CREATED = "order.created"
    ORDER_PAID = "order.paid"
    ORDER_CANCELED = "order.canceled"
    PROVIDER_EXECUTION_FAILED = "provider.execution_failed"
```

Конверт события (формат «на проводе») с метаданными трассировки:

```python
@dataclass(frozen=True)
class EventEnvelope:
    event_id: UUID
    event_type: str
    aggregate_id: str
    occurred_at: datetime
    payload: dict
    schema_version: int
    correlation_id: str        # сквозная трассировка цепочки
    causation_id: UUID | None  # какое событие породило это
    producer: str
```

Детерминированный ключ дедупликации:

```python
def make_dedup_key(event_type: str, aggregate_id: str, idempotency_key: str) -> str:
    # форма: "<event_type>:<aggregate_id>:<idempotency_key>"
    # повтор устойчивых идентификаторов → тот же ключ → дубль схлопывается
    return f"{event_type}:{aggregate_id}:{idempotency_key}"
```

**Как работает.** Продюсер пишет событие с `event_type` из enum, payload-схемой
и envelope (включая `correlation_id`/`causation_id` для трассировки всей
цепочки). `schema_version` в заголовках позволяет менять схему, не ломая старых
консьюмеров. `dedup_key` детерминированно строится из устойчивых
идентификаторов — повтор даёт тот же ключ и схлопывается (см. §10–11).

**Зачем.**
- **Чёткий договор** между сервисами; нельзя прислать «самопальный» тип.
- **Обратная совместимость** через версионирование схемы.
- **Трассируемость** распределённого процесса (correlation/causation).
- **Замкнутая идемпотентность** благодаря детерминированному `dedup_key`.

---

## Как паттерны складываются вместе

Один путь «пользователь инициировал операцию» проходит почти через все паттерны:

1. **Router** (§6) принимает запрос; **Depends** (§7) даёт сессию, текущего
пользователя и нужный вариант сервиса.
2. **Idempotency** (§8) гарантирует, что ретрай не выполнит операцию дважды.
3. **Service** (§2) применяет бизнес-правила, ходит в **Repository** (§1).
4. Смена состояния и `append_event` в **Outbox** (§10) идут в одной
**Unit of Work** транзакции (§3).
5. **Publisher** + **Adapter над брокером** (§12) надёжно публикуют событие.
6. **Orchestrator/Saga** (§13) ведёт процесс по шагам; **Idempotent consumer /
Inbox** (§11) защищает от дублей; при сбое — **компенсация**.
7. Всё связано **Event Contracts** (§14), а собрано через **DI** (§4) с
**DTO/схемами** (§5) на границах.

Если ошибка — **Centralized Error Handling** (§9) превратит доменное исключение
в корректный HTTP-ответ.