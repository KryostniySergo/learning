from pathlib import Path

from collect_data_from_xls import collect_data_from_xls
from download_files import download_files
from db.insert_data_to_db import insert_data_to_db

SCRIPT_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = SCRIPT_DIR / "download"
DOWNLOAD_DIR.mkdir(exist_ok=True)


def run_sync():
    pass


async def run_async():
    pass


if __name__ == "__main__":
    # Проверяем нужно ли заного качать файлы
    if not any(DOWNLOAD_DIR.iterdir()):
        download_files(DOWNLOAD_DIR)
    else:
        print("В папке уже есть файлы, не стану качать их повторно")
    # Формируем таблицу которую потом передадим в БД
    data_from_xls = collect_data_from_xls(DOWNLOAD_DIR)
    # Заносим данные в бдЗ
    insert_data_to_db(data_from_xls)
