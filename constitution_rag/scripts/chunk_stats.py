# scripts/chunk_stats.py
import statistics
from collections import Counter

from app.config import settings
from app.ingest.chunker import build_chunks
from app.ingest.loader import load_text
from app.ingest.parser import parse

units = parse(load_text(settings.source_path))
chunks = build_chunks(units, settings.min_chunk_chars, settings.max_chunk_chars)
lengths = [len(c.quote) for c in chunks]

print(f"единиц: {len(units)}, чанков: {len(chunks)}")
print(f"длина quote: min={min(lengths)} median={statistics.median(lengths):.0f} max={max(lengths)}")
print("по типам:", dict(Counter(c.kind for c in chunks)))
print("слитые:", sum(".." in c.id for c in chunks), " разрезанные:", sum("-c" in c.id for c in chunks))

too_long = [(c.id, len(c.quote)) for c in chunks if len(c.quote) > settings.max_chunk_chars]
print("длиннее лимита (неделимые предложения):", too_long or "нет")

print("\nсамые длинные:")
for c in sorted(chunks, key=lambda c: -len(c.quote))[:5]:
    print(f"  {c.id:20} {len(c.quote):5}  {c.ref}")
