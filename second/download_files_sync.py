import os
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

MAIN_URL = "https://spimex.com"
MAX_PAGE = 100


def save_file(DOWNLOAD_DIR: Path, link):
    parsed = urlparse(link)
    filename = os.path.basename(parsed.path)

    file_path = DOWNLOAD_DIR / filename

    url = f"{MAIN_URL}{link.attrs['href']}"
    response = requests.get(url)
    response.raise_for_status()
    file_path.write_bytes(response.content)
    print(f"Сохранено: {file_path}")


def download_files_sync(DOWNLOAD_DIR: Path):
    for i in range(MAX_PAGE, 1, -1):
        response = requests.get(url=f"{MAIN_URL}/markets/oil_products/trades/results/?page=page-{i}")
        if response.status_code != 200:
            raise Exception(f"Не удалось получить данные со страницы {i}. Возможно проблемы с интернетом")

        soup = BeautifulSoup(response.text, "html.parser")

        links_to_xls = soup.find_all(
            "a",
            class_=lambda c: c and "link" in c.split() and "xls" in c.split(),  # type: ignore
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

            save_file(DOWNLOAD_DIR, link)
        print(f"Обработал страницу: {i}.")
