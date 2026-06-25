from pathlib import Path
from uuid import uuid4

from bs4 import BeautifulSoup
import requests

MAIN_URL = "https://spimex.com"
MAX_PAGE = (
    100  # Используем 100 так как только с этой страницы начинаются данные с 2023 года
)


def download_file_to_dir(DOWNLOAD_DIR: Path, link):

    file_path = DOWNLOAD_DIR / f"{uuid4()}.xls"

    url = f"{MAIN_URL}{link.attrs['href']}"

    response = requests.get(url)
    response.raise_for_status()

    file_path.write_bytes(response.content)

    print(f"Сохранено: {file_path}")


def download_files(DOWNLOAD_DIR: Path):
    for i in range(MAX_PAGE, 1, -1):
        response = requests.get(
            url=f"{MAIN_URL}/markets/oil_products/trades/results/?page=page-{i}"
        )
        if response.status_code != 200:
            raise Exception(
                f"Не удалось получить данные со страницы {i}. Возможно проблемы с интернетом"
            )

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

            download_file_to_dir(DOWNLOAD_DIR, link)
        print(f"Обработал страницу: {i}.")
