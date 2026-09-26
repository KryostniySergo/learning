# scripts/check_loader.py
import re

from app.config import settings
from app.ingest.loader import load_text

text = load_text(settings.source_path)
lines = text.split("\n")

print(f"символов: {len(text)}, строк: {len(lines)}")

# 1. мусорных символов не осталось
for ch, name in [("\xa0", "nbsp"), ("\u00ad", "soft hyphen"), ("\ufeff", "BOM"), ("\u200b", "zwsp")]:
    print(f"{name:12} {'OK' if ch not in text else 'ОСТАЛСЯ!'}")

# 2. ключевые строки есть в чистом виде (строка целиком совпадает)
for probe in ["Статья 1", "Статья 67.1", "Статья 137"]:
    print(f"{probe!r:15} {'OK' if probe in lines else 'НЕ НАЙДЕНА как отдельная строка'}")

# 3. сколько строк похожи на заголовки
print("глав:", sum(bool(re.match(r"^Глава\s+\d+", l)) for l in lines))
print("статей:", sum(bool(re.match(r"^Статья\s+\d+", l)) for l in lines))

# 4. первые строки, чтобы глазами посмотреть формат
print("\n--- начало файла ---")
print("\n".join(lines[:40]))
