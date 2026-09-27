# tests/test_llm_client.py
from types import SimpleNamespace

import pytest
from app.llm.client import LLMTruncatedError, OpenAICompatibleClient, strip_reasoning


def fake_response(content: str | None, finish_reason: str) -> SimpleNamespace:
    """Объект, похожий на ответ openai: resp.choices[0].message.content и finish_reason."""
    message = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=finish_reason)])


def client_returning(response: SimpleNamespace) -> OpenAICompatibleClient:
    """Настоящий клиент, у которого сетевой вызов подменён и возвращает response."""
    client = OpenAICompatibleClient("m", "key", "http://localhost:1/v1", timeout=1)
    create = lambda **kwargs: response
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    return client


def test_strip_reasoning():
    """Блок рассуждений убирается, в том числе незакрытый."""
    assert strip_reasoning("<think>\nхм, думаю\n</think>\n\nОтвет [Статья 3]") == "Ответ [Статья 3]"
    assert strip_reasoning("<think>не успел додумать") == ""
    assert strip_reasoning("Обычный ответ") == "Обычный ответ"


def test_complete_returns_content():
    """Обычный ответ возвращается как есть."""
    client = client_returning(fake_response("Ответ [Статья 3]", "stop"))
    assert client.complete([], max_tokens=100) == "Ответ [Статья 3]"


def test_empty_content_cut_by_length_raises():
    """Пустой content + finish_reason=length — понятная ошибка вместо тихого пустого ответа."""
    client = client_returning(fake_response("", "length"))
    with pytest.raises(LLMTruncatedError):
        client.complete([], max_tokens=50)
