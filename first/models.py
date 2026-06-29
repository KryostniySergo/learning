from datetime import datetime
from decimal import Decimal

from database import BaseModel
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Genre(BaseModel):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)

    books: Mapped[list["Book"]] = relationship(back_populates="genre")


class Author(BaseModel):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=False)

    books: Mapped[list["Book"]] = relationship(back_populates="author")


class Book(BaseModel):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    amount: Mapped[int] = mapped_column(Integer, default=0)

    genre_id: Mapped[int] = mapped_column(Integer, ForeignKey("genre.id"))
    genre: Mapped["Genre"] = relationship(back_populates="books")

    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("author.id"))
    author: Mapped["Author"] = relationship(back_populates="books")

    buy_book: Mapped[list["Buy_book"]] = relationship(back_populates="book")

    created_on: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class City(BaseModel):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)

    delivery_time: Mapped[datetime] = mapped_column(DateTime)

    clients: Mapped[list["Client"]] = relationship(back_populates="city")


class Client(BaseModel):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    email: Mapped[str] = mapped_column(String, unique=True)

    city_id: Mapped[int] = mapped_column(Integer, ForeignKey("city.id"))
    city: Mapped["City"] = relationship(back_populates="clients")

    buys: Mapped[list["Buy"]] = relationship(back_populates="client")


class Buy(BaseModel):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comment: Mapped[str] = mapped_column(String)

    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("client.id"))
    client: Mapped["Client"] = relationship(back_populates="buys")

    buy_book: Mapped[list["Buy_book"]] = relationship(back_populates="buy")
    buy_step: Mapped[list["Buy_step"]] = relationship(back_populates="buy")


class Buy_book(BaseModel):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    amount: Mapped[int] = mapped_column(Integer, default=0)

    book_id: Mapped[int] = mapped_column(Integer, ForeignKey("book.id"))
    book: Mapped["Book"] = relationship(back_populates="buy_book")

    buy_id: Mapped[int] = mapped_column(Integer, ForeignKey("buy.id"))
    buy: Mapped["Buy"] = relationship(back_populates="buy_book")


class Step(BaseModel):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)

    buy_step: Mapped[list["Buy_step"]] = relationship(back_populates="step")


class Buy_step(BaseModel):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    date_created: Mapped[datetime] = mapped_column(DateTime)
    date_completed: Mapped[datetime] = mapped_column(DateTime)

    buy_id: Mapped[int] = mapped_column(Integer, ForeignKey("buy.id"))
    buy: Mapped["Buy"] = relationship(back_populates="buy_step")

    step_id: Mapped[int] = mapped_column(Integer, ForeignKey("step.id"))
    step: Mapped["Step"] = relationship(back_populates="buy_step")
