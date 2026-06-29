"""
Заполнение БД тестовыми данными + проверочные запросы.

Запуск:
    python seed_and_query.py

Скрипт:
  1. Создаёт все 9 таблиц (genre, author, book, city, client,
     buy, buy_book, step, buy_step).
  2. Наполняет их связанными тестовыми данными.
  3. Выполняет 4 проверочных запроса через JOIN / relationship.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from database import BaseModel, SessionLocal, engine
from models import (
    Author,
    Book,
    Buy,
    Buy_book,
    Buy_step,
    City,
    Client,
    Genre,
    Step,
)
from sqlalchemy import select


def reset_schema() -> None:
    """Пересоздаём схему с нуля, чтобы запуск был идемпотентным."""
    BaseModel.metadata.drop_all(engine)
    BaseModel.metadata.create_all(engine)
    print("Схема создана: 9 таблиц ->", ", ".join(BaseModel.metadata.tables))


def seed() -> None:
    """seed Наполняем таблицу"""
    with SessionLocal() as session:
        # --- Справочники ---------------------------------------------------
        fantasy = Genre(name="Фэнтези")
        sci_fi = Genre(name="Научная фантастика")
        detective = Genre(name="Детектив")

        tolkien = Author(name="Дж. Р. Р. Тон")
        asimov = Author(name="Айбек Азимов")
        christie = Author(name="Агата Кристи")

        # --- Книги ---------------------------------------------------------
        b_hobbit = Book(
            title="Хоббит",
            price=Decimal("12.50"),
            amount=10,
            genre=fantasy,
            author=tolkien,
        )
        b_foundation = Book(
            title="Основание",
            price=Decimal("15.30"),
            amount=8,
            genre=sci_fi,
            author=asimov,
        )
        b_orient = Book(
            title="Убийство в Восточном экспрессе",
            price=Decimal("9.99"),
            amount=12,
            genre=detective,
            author=christie,
        )

        # --- Города и клиенты ---------------------------------------------
        riga = City(name="Рига", delivery_time=datetime(2026, 1, 10, 12, 0))
        vilnius = City(name="Вильнюс", delivery_time=datetime(2026, 1, 12, 9, 30))

        alice = Client(name="Alice", email="alice@example.com", city=riga)
        bob = Client(name="Bob", email="bob@example.com", city=vilnius)

        # --- Этапы обработки заказа ---------------------------------------
        s_new = Step(name="Оформлен")
        s_paid = Step(name="Оплачен")
        s_shipped = Step(name="Отправлен")

        # --- Заказ Alice: две книги (M:N через buy_book) -------------------
        buy_alice = Buy(comment="Подарок на день рождения", client=alice)
        buy_alice.buy_book = [
            Buy_book(book=b_hobbit, amount=1),
            Buy_book(book=b_foundation, amount=2),
        ]
        now = datetime(2026, 1, 5, 10, 0)
        buy_alice.buy_step = [
            Buy_step(
                name="Оформлен",
                step=s_new,
                date_created=now,
                date_completed=now + timedelta(hours=1),
            ),
            Buy_step(
                name="Оплачен",
                step=s_paid,
                date_created=now + timedelta(hours=1),
                date_completed=now + timedelta(hours=2),
            ),
        ]

        # --- Заказ Bob: одна книга -----------------------------------------
        buy_bob = Buy(comment="Срочная доставка", client=bob)
        buy_bob.buy_book = [Buy_book(book=b_orient, amount=1)]
        buy_bob.buy_step = [
            Buy_step(
                name="Оформлен",
                step=s_new,
                date_created=now,
                date_completed=now + timedelta(minutes=30),
            ),
            Buy_step(
                name="Отправлен",
                step=s_shipped,
                date_created=now + timedelta(hours=3),
                date_completed=now + timedelta(hours=4),
            ),
        ]

        session.add_all([buy_alice, buy_bob])
        session.commit()
        print("Тестовые данные загружены.\n")


def query_books_by_genre(genre_name: str) -> None:
    """Запрос 1: книги конкретного жанра (JOIN book -> genre)."""
    print(f"[1] Книги жанра «{genre_name}»:")
    with SessionLocal() as session:
        stmt = (
            select(Book.title, Author.name, Book.price)
            .join(Book.genre)
            .join(Book.author)
            .where(Genre.name == genre_name)
            .order_by(Book.title)
        )
        for title, author, price in session.execute(stmt):
            print(f"    - {title} ({author}) — {price} €")
    print()


def query_client_orders(client_name: str) -> None:
    """Запрос 2: заказы клиента + книги в них (relationship + M:N)."""
    print(f"[2] Заказы клиента «{client_name}»:")
    with SessionLocal() as session:
        client = session.scalar(select(Client).where(Client.name == client_name))
        if client is None:
            print("    клиент не найден")
            print()
            return
        for buy in client.buys:
            print(f"    Заказ #{buy.id}: {buy.comment}")
            for bb in buy.buy_book:  # buy -> buy_book -> book (многие-ко-многим)
                print(f"        {bb.book.title} x{bb.amount}")
    print()


def query_order_steps(buy_id: int) -> None:
    """Запрос 3: этапы конкретного заказа с датами (JOIN buy_step -> step)."""
    print(f"[3] Этапы заказа #{buy_id} с датами:")
    with SessionLocal() as session:
        stmt = (
            select(
                Step.name,
                Buy_step.date_created,
                Buy_step.date_completed,
            )
            .join(Buy_step.step)
            .where(Buy_step.buy_id == buy_id)
            .order_by(Buy_step.date_created)
        )
        for step_name, created, completed in session.execute(stmt):
            print(f"    {step_name}: начат {created:%Y-%m-%d %H:%M}, завершён {completed:%Y-%m-%d %H:%M}")
    print()


def query_books_sold_per_client() -> None:
    """Запрос 4: сколько экземпляров книг купил каждый клиент (агрегат + JOIN)."""
    from sqlalchemy import func

    print("[4] Всего куплено экземпляров по клиентам:")
    with SessionLocal() as session:
        stmt = (
            select(Client.name, func.sum(Buy_book.amount))
            .join(Buy, Buy.client_id == Client.id)
            .join(Buy_book, Buy_book.buy_id == Buy.id)
            .group_by(Client.name)
            .order_by(Client.name)
        )
        for name, total in session.execute(stmt):
            print(f"    {name}: {total} шт.")
    print()


if __name__ == "__main__":
    reset_schema()
    seed()
    query_books_by_genre("Фэнтези")
    query_client_orders("Alice")
    query_order_steps(1)
    query_books_sold_per_client()
