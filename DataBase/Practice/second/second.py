from datetime import datetime
from uuid import uuid4
from bs4 import BeautifulSoup
import requests
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = SCRIPT_DIR / "download"
DOWNLOAD_DIR.mkdir(exist_ok=True)
MAIN_URL = "https://spimex.com"

FIELDS = {
    1: "exchange_product_id",  # Код инструмента
    2: "exchange_product_name",  # Наименование инструмента
    3: "delivery_basis_name",  # Базис поставки
    4: "volume",  # Объём договоров в ед. измерения
    5: "total",  # Объём договоров, руб.
    14: "count",  # Количество договоров, шт.
}


def download_file_to_dir(document_date_text: str, link):

    file_path = DOWNLOAD_DIR / f"{document_date_text}_{uuid4()}.xls"

    url = f"{MAIN_URL}{link.attrs['href']}"

    response = requests.get(url)
    response.raise_for_status()

    file_path.write_bytes(response.content)

    print(f"Сохранено: {file_path}")


def download_files():
    for i in range(416, 1, -1):
        response = requests.get(
            url=f"{MAIN_URL}/markets/oil_products/trades/results/?page=page-{i}"
        )
        if response.status_code != 200:
            print(f"Что то пошло не так на странице {i}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        links_to_xls = soup.find_all(
            "a",
            class_=lambda c: c and "link" in c.split() and "xls" in c.split(),
            href=True,
        )

        for link in links_to_xls:
            document_date_text = str(link.parent.parent.find("span").text)
            try:
                year = int(document_date_text.split(".")[2])
            except Exception:
                continue

            if year < 2023:
                continue

            download_file_to_dir(document_date_text, link)
        print(f"Обработал страницу: {i}.")


def read_unit_block(path, unit="Метрическая тонна"):
    raw = pd.read_excel(path, engine="xlrd", header=None, usecols=list(FIELDS))
    raw.columns = list(FIELDS.values())

    code = raw["exchange_product_id"].astype(str)
    unit_col = code.str.extract(r"Единица измерения:\s*(.+)")[0].ffill()

    is_data = code.str.fullmatch(r"[A-Z0-9-]+")  # строка данных = код инструмента
    return raw[is_data & unit_col.eq(unit)].reset_index(drop=True)


def create_virtual_table():

    file_path = "/Users/sergoza/Desktop/MyProjects/rabota_proj/DataBase/Practice/second/download/01.02.2023_32963c84-3afb-49c7-a625-9e8d410b1b9c.xls"

    df = read_unit_block(file_path)
    print(df.head(5))


if __name__ == "__main__":
    # download_files()
    create_virtual_table()
