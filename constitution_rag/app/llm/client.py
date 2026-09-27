# app/llm/client.py
"""Клиент к LLM. Любой OpenAI-совместимый сервер: облако, Ollama, vLLM, LM Studio."""

import re
from typing import Protocol

from openai import OpenAI

# Блок рассуждений "думающих" моделей, если сервер вставляет его прямо в content.
# Может быть не закрыт, если модель упёрлась в max_tokens посреди рассуждения.
RE_THINK = re.compile(r"<think>.*?(</think>|$)", re.DOTALL)


class LLMTruncatedError(RuntimeError):
    """Модель исчерпала max_tokens и не выдала ни слова ответа."""


def strip_reasoning(text: str) -> str:
    """Убирает из ответа блок <think>...</think>, оставляя только итоговый текст."""
    return RE_THINK.sub("", text).strip()


class LLMClient(Protocol):
    """Всё, что нужно сервису от LLM: сообщения на вход, текст на выход.

    Protocol описывает интерфейс без наследования: подойдёт любой объект с таким
    методом complete — настоящий клиент или фейк в тестах.
    """

    def complete(self, messages: list[dict], max_tokens: int) -> str:
        """Возвращает текст ответа модели."""
        ...


class OpenAICompatibleClient:
    """Обёртка над openai.OpenAI с настройками, важными для RAG."""

    def __init__(self, model: str, api_key: str, base_url: str | None, timeout: float) -> None:
        """Создаёт клиента.

        Args:
            model: имя модели на сервере, например "qwen2.5:7b-instruct".
            api_key: ключ; локальным серверам обычно нужен любой непустой.
            base_url: адрес API вместе с /v1, например "http://localhost:1234/v1".
                None — официальный API OpenAI.
            timeout: сколько секунд ждать ответа, прежде чем сдаться.
        """
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=1)
        self._model = model

    def complete(self, messages: list[dict], max_tokens: int) -> str:
        """Один запрос к модели. temperature=0: одинаковый вопрос — одинаковый ответ.

        Raises:
            LLMTruncatedError: ответ пустой, потому что модель упёрлась в max_tokens.
                Типичная причина — "думающая" модель потратила весь лимит на рассуждения.
        """
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.0,
            max_tokens=max_tokens,
        )
        choice = resp.choices[0]
        content = strip_reasoning(choice.message.content or "")
        if not content and choice.finish_reason == "length":
            raise LLMTruncatedError(
                f"модель исчерпала max_tokens={max_tokens} и не дала ответа (похоже, весь лимит ушёл на рассуждения)"
            )
        return content
