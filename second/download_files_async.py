import asyncio
import os
from pathlib import Path
from urllib.parse import urlparse

import aiofiles
import aiohttp
from bs4 import BeautifulSoup

MAIN_URL = "https://spimex.com"
MAX_PAGE = 100  # Используем 100 так как только с этой страницы начинаются данные с 2023 года
CONCURRENT_LIMIT = 5
DELAY_BETWEEN_PAGES = 0.7
TIMEOUT = 30


async def save_file_async(
    session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, DOWNLOAD_DIR: Path, link: str
) -> None:
    # Получаем имя файла
    parsed = urlparse(link)
    filename = os.path.basename(parsed.path)

    file_path = DOWNLOAD_DIR / filename

    async with semaphore:
        url = f"{MAIN_URL}{link}"
        try:
            async with session.get(url, timeout=TIMEOUT) as response:
                response.raise_for_status()
                async with aiofiles.open(file_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)
            print(f"Сохранено: {file_path}")
            await asyncio.sleep(0.3)  # небольшая пауза после успешной скачки
        except Exception as e:
            print(f"Ошибка при скачивании {url}: {e}")


async def collect_links(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore, url: str) -> list[str]:
    async with semaphore:
        try:
            await asyncio.sleep(DELAY_BETWEEN_PAGES)

            async with session.get(url, timeout=TIMEOUT) as response:
                response.raise_for_status()
                html = await response.text()

            soup = BeautifulSoup(html, "html.parser")

            links_to_xls = soup.find_all(
                "a",
                class_=lambda c: c and "link" in c.split() and "xls" in c.split(),  # type: ignore
                href=True,
            )

            useful_links: list[str] = []
            for link in links_to_xls:
                try:
                    # Находим дату
                    date_span = link.parent.parent.find("span")
                    if not date_span:
                        continue
                    document_date_text = str(date_span.text).strip()
                    year = int(document_date_text.split(".")[2])
                    if year >= 2023:
                        useful_links.append(link.attrs["href"])
                except Exception:
                    continue
            return useful_links

        except asyncio.TimeoutError:
            print(f"Таймаут при запросе {url}")
            return []
        except Exception as e:
            print(f"Ошибка при запросе к {url}: {e}")
            return []


async def download_files_async(DOWNLOAD_DIR: Path) -> None:
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)

    connector = aiohttp.TCPConnector(
        limit=CONCURRENT_LIMIT * 2, limit_per_host=CONCURRENT_LIMIT, ssl=False, keepalive_timeout=TIMEOUT
    )

    timeout = aiohttp.ClientTimeout(total=60, sock_connect=15, sock_read=30)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    }

    async with aiohttp.ClientSession(connector=connector, timeout=timeout, headers=headers) as session:
        urls = [f"{MAIN_URL}/markets/oil_products/trades/results/?page=page-{i}" for i in range(MAX_PAGE, 0, -1)]

        print(f"Начинаем сбор ссылок с {len(urls)} страниц...")

        tasks = [collect_links(session, semaphore, url) for url in urls]

        raw_links: list[list[str]] = await asyncio.gather(*tasks, return_exceptions=True)

        # Фильтруем возможные исключения
        filtered_links = []
        for res in raw_links:
            if isinstance(res, list):
                filtered_links.extend(res)
            elif isinstance(res, Exception):
                print(f"Задача упала: {res}")

        print(f"Всего найдено уникальных ссылок: {len(set(filtered_links))}")

        print("Начинаем скачивание...")
        download_tasks = [save_file_async(session, semaphore, DOWNLOAD_DIR, link) for link in filtered_links]

        await asyncio.gather(*download_tasks)

        print("Скачал файлы")
