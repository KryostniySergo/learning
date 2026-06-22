from datetime import datetime
from uuid import uuid4
from bs4 import BeautifulSoup
import requests
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = SCRIPT_DIR / "download"
MAIN_URL = "https://spimex.com"



def download_file_to_dir(document_date_text: str, link):

    file_path = DOWNLOAD_DIR / f"{document_date_text}_{uuid4()}.xls"

    url = f"{MAIN_URL}{link.attrs['href']}"

    response = requests.get(url)
    response.raise_for_status()

    file_path.write_bytes(response.content)

    print(f"Сохранено: {file_path}")



def download_files():
    for i in range(416, 1, -1):
        response = requests.get(url=f"{MAIN_URL}/markets/oil_products/trades/results/?page=page-{i}")
        if response.status_code != 200:
            print(f"Что то пошло не так на странице {i}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        links_to_xls = soup.find_all(
            "a", class_=lambda c: c and "link" in c.split() and "xls" in c.split(), href=True
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

if __name__ == "__main__":
    download_files()