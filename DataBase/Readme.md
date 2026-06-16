# Databases

# Работа с базами данных (PostgreSQL + SQLAlchemy)

Материал для изучения работы с реляционными БД в Python. Состоит из:

- **Теоретической базы** и ссылок для самостоятельного изучения;
- **Настройки окружения** (PostgreSQL + SQLAlchemy, синхронно и асинхронно);
- **Теории** по SQL и SQLAlchemy, покрывающей вопросы для самопроверки;
- **Самостоятельной работы** (два практических задания);
- **Вопросов для подготовки к проверке знаний** + краткий разбор ответов.

---

## Теоретическая база

Одна из самых распространённых реляционных БД в Python-разработке —
**PostgreSQL**. Наиболее популярный способ общения с БД из Python — библиотека
**SQLAlchemy** (ORM + Core).

### Материалы для просмотра

**0. Введение**
- https://youtu.be/bv5UqdWm-5k
- https://youtu.be/WpojDncIWOw

**1. PostgreSQL**
- Начало работы (статья): https://proglib.io/p/learn-postgresql
- Начало работы, Windows: https://www.youtube.com/watch?v=oEi5IUgxaU0
- Начало работы, Linux: https://youtu.be/kWUW3sMK0Mk

**2. SQLAlchemy**
- Базовое представление (на примере SQLite, но это не важно): https://youtu.be/mxOXUCb2V7M
- Статья по быстрому старту: https://metanit.com/python/database/3.3.php
- Примеры запросов через `session.query`: https://habr.com/ru/companies/true_engineering/articles/226521/
- Полезно ознакомиться: https://habr.com/ru/articles/597999/
- Документация (актуальный 2.0 quickstart): https://docs.sqlalchemy.org/en/20/orm/quickstart.html

> Примечание: в статьях часто показывают подключение к SQLite. Ниже — как
подключиться к PostgreSQL.
> 

---

## Настройка окружения

### 1. Файл `.env`

Секреты и параметры подключения держим вне кода, в переменных окружения:

```
DB_NAME=your_name
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASS=your_password
```

> `.env` обязательно добавляем в `.gitignore` — пароли не должны попадать в git.
> 

### 2. Файл `config.py`

Подгружаем данные из окружения:

```python
import os

from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.environ.get("DB_NAME")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
```

> В исходном материале здесь была опечатка `os.environ.gSeet(...)` — правильно
`os.environ.get(...)`.
> 

### 3. Файл `database.py` — синхронная работа

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

BaseModel = declarative_base()

# pool_pre_ping=True — проверять «живость» соединения перед выдачей из пула
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Session = sessionmaker(bind=engine)
```

> В исходнике движок создавался от несуществующей переменной `POSTGRES_URI` —
правильно использовать `DATABASE_URL`.
> 

### 4. Файл `database.py` — асинхронная работа

Для асинхронного драйвера ставим `asyncpg` и используем схему
`postgresql+asyncpg`:

```python
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from .config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

BaseModel = declarative_base()

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
```

`expire_on_commit=False` важен в async-коде: иначе после `commit()` атрибуты
объектов «протухают» и при обращении SQLAlchemy попытается сделать ленивый
синхронный запрос — в async это приведёт к ошибке.

---

## Основы SQLAlchemy 2.0 (ORM)

### Объявление моделей

Современный стиль (типизированный, через `Mapped` / `mapped_column`):

```python
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import BaseModel

class Genre(BaseModel):
    __tablename__ = "genre"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)

    books: Mapped[list["Book"]] = relationship(back_populates="genre")

class Book(BaseModel):
    __tablename__ = "book"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    price: Mapped[Decimal]
    amount: Mapped[int] = mapped_column(default=0)
    genre_id: Mapped[int] = mapped_column(ForeignKey("genre.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("author.id"))

    genre: Mapped["Genre"] = relationship(back_populates="books")
    created_on: Mapped[datetime] = mapped_column(server_default=func.now())
```

### Запросы (стиль 2.0 — `select()`, а не устаревший `session.query`)

```python
from sqlalchemy import select

# выбрать книги дороже 500, по убыванию цены
stmt = select(Book).where(Book.price > 500).order_by(Book.price.desc())
result = await session.scalars(stmt)
books = result.all()

# агрегаты + группировка: количество книг по жанрам
stmt = (
    select(Genre.name, func.count(Book.id))
    .join(Book, Book.genre_id == Genre.id)
    .group_by(Genre.name)
)
rows = (await session.execute(stmt)).all()
```

### Транзакция

```python
async with async_session_factory() as session:
    async with session.begin():        # commit на выходе, rollback при исключении
        session.add(Book(title="...", price=Decimal("199.00"), genre_id=1, author_id=1))
        # ... другие изменения
    # здесь транзакция уже закоммичена
```

---

## Теория (разбор ключевых понятий)

Этот раздел покрывает понятия из вопросов для самопроверки в конце документа.

### СУБД и SQL

- **СУБД (DBMS)** — система управления базами данных: ПО, которое хранит данные,
обеспечивает доступ к ним, целостность, транзакции, безопасность
(PostgreSQL, MySQL, Oracle, SQLite). Реляционная СУБД (РСУБД/RDBMS) хранит
данные в таблицах со связями.
- **SQL** делится на подъязыки:
    - **DDL** (Data Definition Language) — структура: `CREATE`, `ALTER`, `DROP`,
    `TRUNCATE`.
    - **DML** (Data Manipulation Language) — данные: `SELECT`, `INSERT`,
    `UPDATE`, `DELETE`.
    - **DCL** (Data Control Language) — права: `GRANT`, `REVOKE`.
    - **TCL** (Transaction Control Language) — транзакции: `BEGIN`/`COMMIT`/
    `ROLLBACK`/`SAVEPOINT`.

### Соединения (JOIN)

**Соединение (JOIN)** объединяет строки двух (или более) таблиц по условию.

- `INNER JOIN` — только совпавшие строки в обеих таблицах.
- `LEFT JOIN` — все строки левой + совпавшие из правой (несовпавшие → `NULL`).
- `RIGHT JOIN` — все строки правой + совпавшие из левой.
- `FULL OUTER JOIN` — все строки обеих, несовпавшие дополняются `NULL`.
- `CROSS JOIN` — декартово произведение (каждая с каждой).
- `SELF JOIN` — таблица соединяется сама с собой (например, сотрудник →
начальник).

```sql
SELECT b.title, a.name
FROM book b
INNER JOIN author a ON a.id = b.author_id;
```

### Подзапросы (subqueries)

**Подзапрос** — запрос внутри другого запроса. Типы:

- **Скалярный** — возвращает одно значение: `WHERE price > (SELECT AVG(price) FROM book)`.
- **Строковый / возвращающий набор** — используется с `IN`, `ANY`, `ALL`:
`WHERE genre_id IN (SELECT id FROM genre WHERE name = 'SciFi')`.
- **Коррелированный** — ссылается на внешний запрос и вычисляется для каждой его
строки.
- **В `FROM`** (производная таблица) — подзапрос как источник данных.

### Индексы

**Индекс** — структура (чаще B-дерево), ускоряющая поиск строк ценой
дополнительного места и замедления записи (индекс надо поддерживать при
`INSERT`/`UPDATE`/`DELETE`).

- **Кластеризованный индекс** — определяет **физический порядок** строк на диске;
на таблицу он один. (В PostgreSQL «настоящего» постоянного кластеризованного
индекса нет — есть разовая команда `CLUSTER`; в MySQL/InnoDB первичный ключ —
кластеризованный.)
- **Некластеризованный индекс** — отдельная структура с указателями на строки;
их может быть много.

PostgreSQL поддерживает разные виды индексов: B-tree (по умолчанию), Hash, GIN
(для массивов/JSONB/полнотекста), GiST, BRIN, а также частичные
(`WHERE ...`) и функциональные индексы.

### Нормализация и денормализация

- **Нормализация** — разбиение данных на таблицы для устранения избыточности и
аномалий обновления (1NF, 2NF, 3NF …).
- **Денормализация** — намеренное добавление избыточности (дублирование полей,
предрасчитанные агрегаты), чтобы ускорить чтение ценой усложнения записи и
риска рассогласования. Применяют, когда чтения сильно преобладают над
записями.

### ACID

Свойства надёжной транзакции:

- **Atomicity (Атомарность)** — всё-или-ничего: либо все операции применились,
либо ни одной.
- **Consistency (Согласованность)** — транзакция переводит БД из одного
корректного состояния в другое (соблюдаются ограничения, FK, constraints).
- **Isolation (Изолированность)** — параллельные транзакции не мешают друг другу
(степень определяется уровнем изоляции).
- **Durability (Долговечность)** — после `COMMIT` данные сохранятся даже при
сбое (за счёт WAL — write-ahead log).

### Управление транзакциями и уровни изоляции

- **Команды управления:** `BEGIN`/`START TRANSACTION`, `COMMIT`, `ROLLBACK`,
`SAVEPOINT name`, `ROLLBACK TO SAVEPOINT name`, `RELEASE SAVEPOINT`.
- **Уровни изоляции** (от слабого к строгому) и аномалии, которые они допускают:

| Уровень | Грязное чтение | Неповторяющееся чтение | Фантомы |
| --- | --- | --- | --- |
| READ UNCOMMITTED | да* | да | да |
| READ COMMITTED | нет | да | да |
| REPEATABLE READ | нет | нет | да* |
| SERIALIZABLE | нет | нет | нет |
- В PostgreSQL `READ UNCOMMITTED` ведёт себя как `READ COMMITTED` (грязного
чтения нет), а `REPEATABLE READ` дополнительно не допускает фантомов
(реализован через snapshot/MVCC). По умолчанию в PostgreSQL — `READ COMMITTED`.
- **Вложенные транзакции** — в PostgreSQL эмулируются через **SAVEPOINT**: можно
откатить часть работы до точки сохранения, не отменяя всю транзакцию. В
SQLAlchemy это `session.begin_nested()`.

### Курсор

**Курсор** — серверный механизм для построчного (или порционного) перебора
большого результата без загрузки всего набора в память. Нужен, когда результат
слишком велик. В SQLAlchemy для потоковой обработки используют
`stream`/`yield_per`.

### Агрегатные функции и сопоставление с образцом

- **Агрегатные функции:** `COUNT`, `SUM`, `AVG`, `MIN`, `MAX` (а также
`STRING_AGG`, `ARRAY_AGG` в PostgreSQL). Часто с `GROUP BY` и фильтрацией
групп через `HAVING`.
- **Сопоставление с образцом:** оператор **`LIKE`** (и `ILIKE` —
регистронезависимый в PostgreSQL). Шаблоны: `%` — любое число символов,
`_` — один символ. Также есть `SIMILAR TO` и регулярки `~`.

### Оптимизация запросов

- Добавить **индексы** на колонки в `WHERE`, `JOIN`, `ORDER BY`.
- Выбирать только нужные колонки (`SELECT col`, а не `SELECT *`).
- Избегать проблемы **N+1** (см. `selectinload`/`joinedload` ниже).
- Анализировать план через **`EXPLAIN` / `EXPLAIN ANALYZE`**.
- Держать статистику свежей (`ANALYZE`), чистить мусор (`VACUUM`).
- Использовать пагинацию, избегать функций над индексируемой колонкой в `WHERE`.

### EXPLAIN, EXPLAIN ANALYZE, VACUUM

- **`EXPLAIN`** — показывает **план** выполнения запроса (как планировщик
собирается его выполнять) с оценками стоимости, **без выполнения**.
- **`EXPLAIN ANALYZE`** — **реально выполняет** запрос и показывает фактическое
время и число строк на каждом шаге. (Осторожно: `EXPLAIN ANALYZE` на
`UPDATE`/`DELETE` действительно меняет данные — оборачивайте в транзакцию с
откатом.)
- **`VACUUM`** — в PostgreSQL из-за MVCC старые версии строк («мёртвые кортежи»)
остаются после `UPDATE`/`DELETE`. `VACUUM` освобождает их; `VACUUM FULL`
физически сжимает таблицу (с блокировкой); `ANALYZE` обновляет статистику для
планировщика. Обычно работает **autovacuum**.

### PostgreSQL vs MySQL (кратко)

- PostgreSQL — более «строгая», объектно-реляционная СУБД с богатой поддержкой
типов (JSONB, массивы, кастомные типы), оконных функций, CTE, расширений
(PostGIS, pgvector), строгого SQL-стандарта и продвинутого MVCC.
- MySQL — исторически быстрее на простых читающих нагрузках, проще, очень
популярна в вебе; движок InnoDB даёт транзакции и FK. Различия по умолчанию в
репликации, типах, обработке `NULL`/строк.
- Для финтеха/сложной аналитики чаще выбирают PostgreSQL.

### Понятия SQLAlchemy

- **Metadata** — реестр (`MetaData`), хранящий описание всех таблиц/схем
(объекты `Table`, колонки, ограничения, индексы). Из него `create_all()`
генерирует DDL; Alembic использует его для автогенерации миграций. У
declarative-базы metadata доступна как `BaseModel.metadata`.
- **`selectinload` vs `joinedload`** (стратегии загрузки связей, борьба с N+1):
    - `joinedload` — подтягивает связь **одним запросом через JOIN**. Хорош для
    «многие-к-одному»/«один-к-одному»; на «один-ко-многим» раздувает результат
    (декартово умножение строк).
    - `selectinload` — делает **отдельный запрос** `WHERE id IN (...)` для
    связанных объектов. Обычно лучше для коллекций («один-ко-многим»): нет
    дублирования строк, всего два запроса вместо N+1.
- **Подключение (connection) vs сессия (session):**
    - **Engine/Connection** — низкоуровневое соединение с БД (Core): выполняет
    SQL, управляет пулом соединений.
    - **Session** (ORM) — рабочая единица поверх соединения: отслеживает объекты
    (identity map), накапливает изменения и сбрасывает их в БД (`flush`),
    управляет транзакцией. Грубо: connection — «провод» к БД, session — «рабочий
    стол» с объектами и транзакцией.
- **Защита от SQL-инъекций:** никогда не склеивать SQL строками с пользовательским
вводом. Использовать **параметризованные запросы** / выражения ORM
(`select(Book).where(Book.title == user_input)`) — значения передаются как
bind-параметры, а не как часть текста запроса. Если нужен сырой SQL — только
через `text()` с именованными параметрами:
`text("... WHERE id = :id"), {"id": user_id}`.

---

## Самостоятельная работа

Два задания: первое — на проектирование схемы и связей (учебное), второе —
полноценный мини-проект «спарсить → разобрать → сохранить» (близко к реальной
работе).

### Задание 1 — схема БД книжного магазина (учебное)

**Цель.** Спроектировать и создать схему БД книжного интернет-магазина на
SQLAlchemy + PostgreSQL. Отработать первичные/внешние ключи, `relationship`,
связи «один-ко-многим» и «многие-ко-многим».

**Что должно получиться — 9 таблиц:**

| Таблица | Поля | Связи |
| --- | --- | --- |
| `genre` | `id`, название жанра | ← `book` |
| `author` | `id`, имя автора | ← `book` |
| `book` | `id`, название, цена, количество на складе, `genre_id`, `author_id` | → `genre`, `author` |
| `city` | `id`, название города, время доставки | ← `client` |
| `client` | `id`, имя, email, `city_id` | → `city`, ← `buy` |
| `buy` | `id`, пожелания покупателя, `client_id` | → `client`, ← `buy_book`, `buy_step` |
| `buy_book` | `id`, количество, `book_id`, `buy_id` | связка `buy` ↔︎ `book` (M:N) |
| `step` | `id`, название этапа обработки заказа | ← `buy_step` |
| `buy_step` | `id`, дата начала, дата окончания, `buy_id`, `step_id` | связка `buy` ↔︎ `step` (M:N) |

**Шаги выполнения:**

1. Настроить подключение к PostgreSQL (см. раздел «Настройка окружения»).
2. Описать 9 моделей через `Mapped` / `mapped_column`, проставить `ForeignKey`
и `relationship` с `back_populates`.
3. Создать схему: `BaseModel.metadata.create_all(engine)` (или сделать миграцию
через Alembic).
4. Заполнить таблицы тестовыми данными и написать 3-4 проверочных запроса
(например: книги жанра X, заказы клиента Y, этапы конкретного заказа с
датами).

**Критерии приёмки:**
- [ ] Все 9 таблиц создаются без ошибок, FK расставлены корректно.
- [ ] Связки `buy_book` и `buy_step` действительно реализуют «многие-ко-многим».
- [ ] Проверочные запросы используют `JOIN` / `relationship` и возвращают
ожидаемые данные.

### Задание 2 — парсер итогов торгов СПбМТСБ (мини-проект)

**Цель.** Написать парсер, который скачивает бюллетени по итогам торгов с сайта
биржи, извлекает нужные данные и складывает их в PostgreSQL.

**Источник:** https://spimex.com/markets/oil_products/trades/results/

**Шаг 1. Скачать бюллетени.** Со страницы результатов забрать файлы-бюллетени
(XLS) **за период начиная с 2023 года**.

**Шаг 2. Разобрать данные.** Из каждого бюллетеня взять строки **только** из
блока «Единица измерения: Метрическая тонна» и **только** там, где
«Количество Договоров, шт.» **> 0**. Нужные столбцы:

| Столбец бюллетеня | Поле |
| --- | --- |
| Код Инструмента | `exchange_product_id` |
| Наименование Инструмента | `exchange_product_name` |
| Базис поставки | `delivery_basis_name` |
| Объём Договоров в единицах измерения | `volume` |
| Объём Договоров, руб. | `total` |
| Количество Договоров, шт. | `count` |

**Шаг 3. Сохранить в таблицу `spimex_trading_results`.** Часть полей —
вычисляемые из кода инструмента (срезы строки):

| Поле | Источник / как получить |
| --- | --- |
| `id` | первичный ключ (автоинкремент) |
| `exchange_product_id` | код инструмента из бюллетеня |
| `exchange_product_name` | наименование из бюллетеня |
| `oil_id` | `exchange_product_id[:4]` |
| `delivery_basis_id` | `exchange_product_id[4:7]` |
| `delivery_basis_name` | базис поставки из бюллетеня |
| `delivery_type_id` | `exchange_product_id[-1]` |
| `volume` | объём в ед. измерения |
| `total` | объём, руб. |
| `count` | количество договоров |
| `date` | дата торгов (из имени файла/страницы бюллетеня) |
| `created_on` | дата создания записи (`server_default=func.now()`) |
| `updated_on` | дата обновления записи (`onupdate=func.now()`) |

**Критерии приёмки:**
- [ ] В БД лежат итоги торгов начиная с 2023 года.
- [ ] Отфильтрованы только метрические тонны и строки с `count > 0`.
- [ ] Поля `oil_id` / `delivery_basis_id` / `delivery_type_id` корректно
вычислены из `exchange_product_id`.
- [ ] Повторный запуск парсера не плодит дубликаты (идемпотентность по дате +
коду инструмента).

**Подсказки и библиотеки:**
- Скачивание: `requests` / `httpx` / `urllib` (при проблемах с сертификатом —
модуль `ssl`).
- Разбор XLS: `pandas` + движок `xlrd` (старый `.xls`) или `openpyxl` (`.xlsx`).
- Работа с БД: `SQLAlchemy` (модель + bulk-вставка).
- Полезно вынести логику в три слоя: *загрузка файла → парсинг в объекты →
сохранение в БД* — так проще тестировать каждый шаг отдельно.

---

## Вопросы для подготовки к проверке знаний

Сначала попробуйте ответить сами, затем сверьтесь с разбором ниже.

1. Что подразумевается под СУБД?
2. Что такое соединения (JOIN) в SQL?
3. Какие типы соединений вы знаете?
4. Что такое индекс?
5. В чём разница между кластеризованным и некластеризованным индексами?
6. Что вы подразумеваете под денормализацией?
7. Что такое свойство ACID в базе данных?
8. Что такое подзапрос в SQL?
9. Какие бывают типы подзапросов?
10. Какие существуют способы оптимизации запроса?
11. Назовите оператор для сопоставления с образцом.
12. Что такое DDL и DML?
13. Какие агрегатные функции вы знаете?
14. Какие команды управления транзакциями вы знаете?
15. Что такое уровни изолированности транзакций?
16. Что такое вложенные транзакции?
17. Что такое курсор и зачем он нужен?
18. Какая разница между PostgreSQL и MySQL?
19. Что такое VACUUM в PostgreSQL?
20. Что такое EXPLAIN?
21. Какая разница между EXPLAIN и EXPLAIN ANALYZE?
22. Для чего нужна Metadata в SQLAlchemy?
23. В чём разница между `selectinload` и `joinedload`?
24. Как избежать SQL-инъекций?
25. В чём разница между подключением (connection) и сессией (session)?

### Краткий разбор ответов

1. **СУБД** — ПО для хранения данных и управления доступом, целостностью,
транзакциями и безопасностью (PostgreSQL, MySQL, …). См. «СУБД и SQL».
2. **JOIN** — объединение строк нескольких таблиц по условию связи.
3. `INNER`, `LEFT`, `RIGHT`, `FULL OUTER`, `CROSS`, `SELF`.
4. **Индекс** — структура (обычно B-дерево), ускоряющая поиск ценой места и
замедления записи.
5. Кластеризованный задаёт **физический порядок** строк (один на таблицу);
некластеризованный — отдельная структура с указателями (их много). В
PostgreSQL постоянного кластеризованного индекса нет.
6. **Денормализация** — намеренная избыточность ради скорости чтения; цена —
сложнее запись и риск рассогласования.
7. **ACID** — Atomicity, Consistency, Isolation, Durability. См. раздел ACID.
8. **Подзапрос** — запрос внутри другого запроса.
9. Скалярный, возвращающий набор (`IN`/`ANY`/`ALL`), коррелированный, подзапрос
в `FROM`.
10. Индексы, выборка только нужных колонок, борьба с N+1, `EXPLAIN ANALYZE`,
свежая статистика (`ANALYZE`/`VACUUM`), пагинация, отказ от функций над
индексируемой колонкой в `WHERE`.
11. **`LIKE`** (и `ILIKE` в PostgreSQL); шаблоны `%` и `_`.
12. **DDL** — определение структуры (`CREATE`/`ALTER`/`DROP`); **DML** —
манипуляция данными (`SELECT`/`INSERT`/`UPDATE`/`DELETE`).
13. `COUNT`, `SUM`, `AVG`, `MIN`, `MAX` (+ `STRING_AGG`, `ARRAY_AGG`).
14. `BEGIN`, `COMMIT`, `ROLLBACK`, `SAVEPOINT`, `ROLLBACK TO SAVEPOINT`,
`RELEASE SAVEPOINT`.
15. Степень изоляции параллельных транзакций: `READ UNCOMMITTED`,
`READ COMMITTED`, `REPEATABLE READ`, `SERIALIZABLE` — см. таблицу аномалий.
16. Транзакции внутри транзакции; в PostgreSQL реализуются через `SAVEPOINT`
(в SQLAlchemy — `begin_nested()`).
17. **Курсор** — построчный/порционный перебор большого результата без загрузки
всего в память.
18. PostgreSQL — строже, богаче типами (JSONB, массивы), сильный MVCC, ближе к
SQL-стандарту; MySQL — проще, исторически быстрее на простых чтениях. См.
раздел сравнения.
19. **`VACUUM`** — очистка «мёртвых» версий строк (следствие MVCC); `VACUUM FULL`
сжимает таблицу; `ANALYZE` обновляет статистику.
20. **`EXPLAIN`** — показывает план выполнения **без** запуска запроса.
21. `EXPLAIN ANALYZE` **реально выполняет** запрос и показывает фактические
время/строки; `EXPLAIN` — только оценки плана.
22. **Metadata** — реестр описаний таблиц/схем; из него генерируется DDL и
миграции (Alembic).
23. `joinedload` — один запрос через `JOIN` (хорош для «к-одному»);
`selectinload` — отдельный запрос `IN (...)` (лучше для коллекций, без
дублирования строк). Оба решают проблему N+1.
24. Параметризованные запросы / выражения ORM; не склеивать SQL строками; сырой
SQL — только через `text()` с bind-параметрами.
25. Connection (Core) — низкоуровневое соединение/пул; Session (ORM) — единица
работы поверх соединения с identity map, отслеживанием изменений и
транзакцией.