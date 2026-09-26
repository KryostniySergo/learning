# app/ingest/loader.py
import re
import unicodedata
from pathlib import Path

# Невидимые символы, которые часто приезжают при копировании с сайтов и из Word
_INVISIBLE = {
    "\u00ad": "",  # мягкий перенос
    "\u200b": "",  # пробел нулевой ширины
    "\u200c": "",
    "\u200d": "",
    "\u2060": "",  # word joiner
    "\ufeff": "",  # BOM, если оказался не в начале файла
}

# Все "пробелоподобные" символы -> обычный пробел
_SPACES = {
    "\u00a0": " ",  # неразрывный пробел
    "\u2007": " ",
    "\u202f": " ",  # узкий неразрывный пробел
    "\t": " ",
}

# Дефисы разной длины -> обычный дефис. Длинное тире (—) оставляем:
# в тексте закона это знак препинания, а не дефис.
_DASHES = {
    "\u2010": "-",
    "\u2011": "-",  # неразрывный дефис
    "\u2012": "-",
    "\u2013": "-",  # короткое тире (en dash)
    "\u2212": "-",  # знак минуса
}

# "Английские" кавычки -> русские ёлочки не делаем (легко ошибиться с парностью),
# просто приводим к одному виду прямых кавычек.
_QUOTES = {
    "\u201c": '"',  # “
    "\u201d": '"',  # ”
    "\u201e": '"',  # „
    "\u201f": '"',
}

_TRANSLATION = str.maketrans({**_INVISIBLE, **_SPACES, **_DASHES, **_QUOTES})


def normalize(text: str) -> str:
    """Приводит текст к предсказуемому виду для парсера.

    Результат: строки без пробелов по краям, одиночные пробелы внутри строк,
    не больше одной пустой строки подряд, только \\n в качестве переноса.
    """  # noqa: D301
    # NFC склеивает "е + диакритика" в "ё" и т.п., но не трогает смысл символов
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_TRANSLATION)

    # единый формат переноса строк
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # несколько пробелов подряд -> один; пробелы по краям строк -> убрать
    lines = [re.sub(r" {2,}", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # 3+ переноса (т.е. 2+ пустых строки подряд) -> одна пустая строка
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_text(path: Path) -> str:
    """Читает исходник в UTF-8 и возвращает нормализованный текст."""
    if not path.exists():
        raise FileNotFoundError(f"Нет файла источника: {path}")
    try:
        # utf-8-sig сам отрезает BOM в начале файла (его ставит Блокнот Windows)
        raw = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Файл {path} не в UTF-8.") from exc

    if not raw.strip():
        raise ValueError(f"Пустой файл источника: {path}")

    return normalize(raw)
