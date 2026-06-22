from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import BaseModel


class Spimex_trading_results(BaseModel):
    __tablename__ = "Spimex_trading_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    exchange_product_id: Mapped[int] = mapped_column(Integer, default=0)
    exchange_product_name: Mapped[str] = mapped_column(String)

    oil_id: Mapped[int] = mapped_column(Integer, default=0)

    delivery_basis_id: Mapped[int] = mapped_column(Integer, default=0)
    delivery_basis_name: Mapped[str] = mapped_column(String)
    delivery_type_id: Mapped[int] = mapped_column(Integer, default=0)

    volume: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    count: Mapped[int] = mapped_column(Integer, default=0)

    date: Mapped[datetime] = mapped_column(DateTime)
    created_on: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_on: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
