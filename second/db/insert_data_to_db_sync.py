import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from db.database_sync import BaseModel, SessionLocal, engine
from db.model import Spimex_trading_results


def reset_schema() -> None:
    """Пересоздаём схему с нуля, чтобы запуск был идемпотентным."""
    BaseModel.metadata.drop_all(engine)
    BaseModel.metadata.create_all(engine)
    print("Схема создана: таблица ->", ", ".join(BaseModel.metadata.tables))


def insert_data_to_db_sync(df: pd.DataFrame):
    reset_schema()

    records = [
        {str(k): v for k, v in row.items()} for row in df.to_dict(orient="records")
    ]
    with SessionLocal() as session:
        stmt = insert(Spimex_trading_results).on_conflict_do_nothing(
            index_elements=["date", "exchange_product_id"]
        )
        session.execute(stmt, records)
        session.commit()
    print("Добавил данные в БД")
