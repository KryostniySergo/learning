import asyncio
from pathlib import Path
from uuid import uuid4

import itertools
import aiohttp
import aiofiles
from bs4 import BeautifulSoup
import requests

MAIN_URL = "https://spimex.com"
MAX_PAGE = (
    100  # Используем 100 так как только с этой страницы начинаются данные с 2023 года
)


def save_file(DOWNLOAD_DIR: Path, link):

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

            save_file(DOWNLOAD_DIR, link)
        print(f"Обработал страницу: {i}.")


async def save_file_async(
    session: aiohttp.ClientSession, DOWNLOAD_DIR: Path, link: str
):
    file_path = DOWNLOAD_DIR / f"{uuid4()}.xls"

    url = f"{MAIN_URL}{link}"

    async with session.get(url) as response:
        response.raise_for_status()
        async with aiofiles.open(file_path, "wb") as f:
            async for chunk in response.content.iter_chunked(8192):
                await f.write(chunk)
    print(f"Сохранено: {file_path}")


async def collect_links(session: aiohttp.ClientSession, url):
    try:
        async with session.get(url) as response:
            # Ждем и читаем содержимое страницы
            html = await response.text()

            soup = BeautifulSoup(html, "html.parser")

            links_to_xls = soup.find_all(
                "a",
                class_=lambda c: c and "link" in c.split() and "xls" in c.split(),  # type: ignore
                href=True,
            )

            usefull_links: list[str] = []
            for link in links_to_xls:
                document_date_text = str(link.parent.parent.find("span").text)
                try:
                    year = int(document_date_text.split(".")[2])
                except Exception:
                    continue

                if year < 2023:
                    continue

                print(link)
                usefull_links.append(link.attrs["href"])

            return usefull_links

    except Exception as e:
        print(f"Ошибка при запросе к {url}: {e}")
        return []


async def download_files_async(DOWNLOAD_DIR: Path):
    urls = [
        f"{MAIN_URL}/markets/oil_products/trades/results/?page=page-{i}"
        for i in range(MAX_PAGE, 1, -1)
    ]
    print(f"Создал набор ulrs")

    async with aiohttp.ClientSession() as session:
        tasks = [collect_links(session, url) for url in urls]

        raw_links: list[list[str]] = await asyncio.gather(*tasks)

        print("Получил все ссылки")

        filtered_links = list(itertools.chain.from_iterable(raw_links))

        download_tasks = [
            save_file_async(session, DOWNLOAD_DIR, link) for link in filtered_links
        ]

        await asyncio.gather(*download_tasks)

        print("Скачал файлы")


SCRIPT_DIR = Path("/root/projects/learning/second")
DOWNLOAD_DIR = SCRIPT_DIR / "download"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# asyncio.run(download_files_async(DOWNLOAD_DIR))

download_files(DOWNLOAD_DIR)
