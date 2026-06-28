import asyncio
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

import pandas as pd


class Field:
    EXCHANGE_PRODUCT_ID = "exchange_product_id"
    EXCHANGE_PRODUCT_NAME = "exchange_product_name"
    DELIVERY_BASIS_NAME = "delivery_basis_name"
    VOLUME = "volume"
    TOTAL = "total"
    COUNT = "count"
    OIL_ID = "oil_id"
    DELIVERY_BASIS_ID = "delivery_basis_id"
    DELIVERY_TYPE_ID = "delivery_type_id"
    TRADE_DATE = "date"


COLUMNS = {
    1: Field.EXCHANGE_PRODUCT_ID,  # Код инструмента
    2: Field.EXCHANGE_PRODUCT_NAME,  # Наименование инструмента
    3: Field.DELIVERY_BASIS_NAME,  # Базис поставки
    4: Field.VOLUME,  # Объём договоров в ед. измерения
    5: Field.TOTAL,  # Объём договоров, руб.
    14: Field.COUNT,  # Количество договоров, шт.
}


def read_xls(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, engine="xlrd", header=None, usecols=list(COLUMNS))
    df.columns = list(COLUMNS.values())
    return df


def extract_date(df: pd.DataFrame) -> datetime:
    marker = df[Field.EXCHANGE_PRODUCT_ID].astype(str)
    trade_date = marker.str.extract(r"Дата торгов:\s*(\d{2}\.\d{2}\.\d{4})")[0].dropna()
    trade_date = (
        pd.to_datetime(trade_date.iloc[0], format="%d.%m.%Y").date()
        if len(trade_date)
        else None
    )
    if not trade_date:
        raise Exception("Не удалось получить дату из документа")

    return trade_date


def filter_df(df: pd.DataFrame, unit="Метрическая тонна"):
    marker = df[Field.EXCHANGE_PRODUCT_ID].astype(str)
    unit_col = marker.str.extract(r"Единица измерения:\s*(.+)")[0].ffill()

    is_data = marker.str.fullmatch(r"[A-Z0-9-]+")
    df = df[is_data & unit_col.eq(unit)].reset_index(drop=True)

    for c in [Field.VOLUME, Field.TOTAL, Field.COUNT]:
        df[c] = pd.to_numeric(df[c].replace("-", pd.NA), errors="coerce").astype(
            "Int64"
        )

    df = df[df["count"] > 0]

    return df


def evaluate_additional_columns(df: pd.DataFrame, trade_date: datetime) -> None:
    df[Field.OIL_ID] = df[Field.EXCHANGE_PRODUCT_ID].str[:4]
    df[Field.DELIVERY_BASIS_ID] = df[Field.EXCHANGE_PRODUCT_ID].str[4:7]
    df[Field.DELIVERY_TYPE_ID] = df[Field.EXCHANGE_PRODUCT_ID].str[-1]
    df[Field.TRADE_DATE] = trade_date


def collect_data_from_xls_sync(DOWNLOAD_DIR: Path) -> pd.DataFrame:
    result_data_dfs: list[pd.DataFrame] = []
    xls_amount = len(list(DOWNLOAD_DIR.iterdir()))
    for i, file in enumerate(DOWNLOAD_DIR.iterdir()):
        df = read_xls(str(file))
        trade_date = extract_date(df)
        filtered_df = filter_df(df)
        evaluate_additional_columns(filtered_df, trade_date)
        result_data_dfs.append(filtered_df)
        print(f"Обработал {i} xls файлов из {xls_amount}")
    result_df = pd.concat(result_data_dfs, axis=0, ignore_index=True)
    return result_df


def process_file(file: Path) -> pd.DataFrame:
    df = read_xls(str(file))
    trade_date = extract_date(df)
    filtered_df = filter_df(df)
    evaluate_additional_columns(filtered_df, trade_date)
    return filtered_df


async def collect_data_from_xls_async(DOWNLOAD_DIR: Path) -> pd.DataFrame:
    files = [f for f in DOWNLOAD_DIR.iterdir() if f.is_file()]
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor() as executor:
        tasks = [loop.run_in_executor(executor, process_file, f) for f in files]
        result_data_dfs = await asyncio.gather(*tasks)
    return pd.concat(result_data_dfs, axis=0, ignore_index=True)
