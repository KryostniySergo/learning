from pathlib import Path

from collect_data_from_xls import (
    collect_data_from_xls_async,
    collect_data_from_xls_sync,
)
from download_files import download_files_sync, download_files_async
from db.insert_data_to_db_sync import insert_data_to_db_sync
from db.insert_data_to_db_async import insert_data_to_db_async
import asyncio
import time

SCRIPT_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = SCRIPT_DIR / "download"
DOWNLOAD_DIR.mkdir(exist_ok=True)


def run_sync():
    download_files_sync(DOWNLOAD_DIR)
    df = collect_data_from_xls_sync(DOWNLOAD_DIR)
    insert_data_to_db_sync(df)


async def run_async():
    await download_files_async(DOWNLOAD_DIR)
    df = await collect_data_from_xls_async(DOWNLOAD_DIR)
    await insert_data_to_db_async(df)


if __name__ == "__main__":
    print("Какой вариант запустить?")
    user_input = input("1) Async\n2) Sync\n3) Оба с замером скорости")
    match user_input:
        case 1:
            start = time.perf_counter()
            asyncio.run(run_async())
            elapsed = time.perf_counter() - start
            print(f"Время выполнения: {elapsed:.6f} сек")
        case 2:
            start = time.perf_counter()
            run_sync()
            elapsed = time.perf_counter() - start
            print(f"Время выполнения: {elapsed:.6f} сек")
        case 3:
            start = time.perf_counter()
            asyncio.run(run_async())
            elapsed_async = time.perf_counter() - start
            print(f"Время выполнения async: {elapsed_async:.6f} сек")

            start = time.perf_counter()
            run_sync()
            elapsed_sync = time.perf_counter() - start
            print(f"Время выполнения sync: {elapsed_sync:.6f} сек")

            diff = elapsed_sync - elapsed_async
            faster = "async" if elapsed_async < elapsed_sync else "sync"
            ratio = max(elapsed_async, elapsed_sync) / min(elapsed_async, elapsed_sync)

            print(f"Быстрее: {faster}")
            print(f"Разница: {abs(diff):.6f} сек")
            print(f"Во сколько раз: {ratio:.2f}x")
        case _:
            print("Неправильный ввод, попробуй набрать цифру от 1 до 3")
