import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from db.database_async import engine, AsyncSessionLocal
from db.database_sync import BaseModel
from db.model import Spimex_trading_results


async def reset_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)
        await conn.run_sync(BaseModel.metadata.create_all)
        print("Схема создана: таблица ->", ", ".join(BaseModel.metadata.tables))


async def insert_data_to_db_async(df: pd.DataFrame):
    await reset_schema()  # тоже должна стать async, см. ниже

    records = [
        {str(k): v for k, v in row.items()} for row in df.to_dict(orient="records")
    ]
    async with AsyncSessionLocal() as session:
        stmt = insert(Spimex_trading_results).on_conflict_do_nothing(
            index_elements=["date", "exchange_product_id"]
        )
        await session.execute(stmt, records)
        await session.commit()
    print("Добавил данные в БД")
