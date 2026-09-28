import argparse
import json
import sys

from app.config import settings
from app.llm.rag import PROMPT_VERSION, build_messages
from app.search.store import ChromaStore


def find_ask_event(lines, request_id: str) -> dict | None:
    """Последнее событие "ask" с нужным request_id среди строк лога."""
    found = None
    for line in lines:
        start = line.find("{")
        if start == -1:
            continue
        try:
            event = json.loads(line[start:])
        except json.JSONDecodeError:
            continue
        if event.get("event") == "ask" and event.get("request_id") == request_id:
            found = event
    return found


def main() -> None:
    """Находит событие в логе, достаёт фрагменты по id из хранилища и печатает промпт."""
    ap = argparse.ArgumentParser(description="Показать промпт, который видела модель")
    ap.add_argument("log", help="файл лога или - для чтения из stdin")
    ap.add_argument("--request-id", required=True)
    args = ap.parse_args()

    source = sys.stdin if args.log == "-" else open(args.log, encoding="utf-8")
    with source:
        event = find_ask_event(source, args.request_id)
    if event is None:
        raise SystemExit(f"событие ask с request_id={args.request_id} не найдено")

    if event.get("prompt_version") != PROMPT_VERSION:
        print(
            f"ВНИМАНИЕ: запрос обработан промптом {event.get('prompt_version')}, "
            f"а в коде сейчас {PROMPT_VERSION} — системная часть может отличаться\n"
        )

    ids = [h["id"] for h in event.get("hits", [])]
    store = ChromaStore(settings.chroma_path, settings.collection_name)
    by_id = store.get_by_ids(ids)
    missing = [i for i in ids if i not in by_id]
    if missing:
        print(f"ВНИМАНИЕ: этих фрагментов уже нет в индексе (переиндексация?): {missing}\n")
    hits = [by_id[i] for i in ids if i in by_id]  # порядок — как в логе, то есть как в промпте

    print(f"вопрос: {event['question']}")
    print(f"маршрут: {event.get('route')}, лучший скор: {event.get('best_score')}, LLM: {event.get('llm_status')}\n")
    if not hits:
        print("модель не вызывалась: фрагментов не было")
        return
    for message in build_messages(event["question"], hits):
        print(f"===== {message['role']} =====\n{message['content']}\n")
    if event.get("answer"):
        print(f"===== ответ модели =====\n{event['answer']}")


if __name__ == "__main__":
    main()
