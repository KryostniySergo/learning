from datetime import datetime

from sqlalchemy import (
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from db.database import BaseModel


class Spimex_trading_results(BaseModel):
    __table_args__ = (
        UniqueConstraint("date", "exchange_product_id", name="uq_date_product"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    exchange_product_id: Mapped[str] = mapped_column(String)
    exchange_product_name: Mapped[str] = mapped_column(String)
    oil_id: Mapped[str] = mapped_column(String)
    delivery_basis_id: Mapped[str] = mapped_column(String)
    delivery_basis_name: Mapped[str] = mapped_column(String)
    delivery_type_id: Mapped[str] = mapped_column(String)

    volume: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    count: Mapped[int] = mapped_column(Integer, default=0)

    date: Mapped[datetime] = mapped_column(DateTime)
    created_on: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_on: Mapped[datetime] = mapped_column(
        DateTime, onupdate=func.now(), nullable=True
    )
