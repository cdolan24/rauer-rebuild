from __future__ import annotations

from unittest.mock import MagicMock

import anthropic
import httpx
import pytest

from src.utils.chat_backend import (
    AnthropicChatBackend,
    ChatBackendError,
    OllamaChatBackend,
    build_chat_backend,
)
from src.utils.config import Config, HostedLlmConfig, OllamaConfig
from src.utils.ollama_client import OllamaError


class _FakeOllamaClient:
    def __init__(self) -> None:
        self.chat_calls: list[dict] = []

    def chat(self, model, messages, temperature=0.7, num_predict=None, keep_alive=None):
        self.chat_calls.append(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "num_predict": num_predict,
                "keep_alive": keep_alive,
            }
        )
        return "a reply"

    def chat_stream(self, model, messages, temperature=0.7, num_predict=None, keep_alive=None):
        yield "frag1"
        yield "frag2"

    def is_healthy(self):
        return True, ["llama3.2:latest"]


class _FailingOllamaClient:
    def chat(self, *a, **kw):
        raise OllamaError("unreachable")

    def chat_stream(self, *a, **kw):
        raise OllamaError("unreachable")
        yield  # pragma: no cover - unreachable, satisfies generator shape


def _config(chat_backend: str = "ollama", api_key: str | None = None) -> Config:
    return Config(
        ollama=OllamaConfig(
            base_url="http://localhost:11434",
            chat_model="llama3.2:latest",
            embedding_model="nomic-embed-text:latest",
            request_timeout=60.0,
            num_predict=512,
            keep_alive="30m",
        ),
        chunking=None,
        vector_db=None,
        data_storage_path="./data_storage/db.sqlite",
        paths=None,
        api=None,
        frontend=None,
        log_level="INFO",
        rag_min_score=0.55,
        rag_max_history_turns=3,
        admin_password=None,
        controller_port=8100,
        controller_url="http://127.0.0.1:8100",
        chat_backend=chat_backend,
        hosted_llm=HostedLlmConfig(
            provider="anthropic", model="claude-haiku-4-5", api_key=api_key, max_tokens=1024
        ),
    )


def test_ollama_chat_backend_delegates_to_client():
    fake_client = _FakeOllamaClient()
    backend = OllamaChatBackend(fake_client, "llama3.2:latest", "30m")

    result = backend.chat([{"role": "user", "content": "hi"}], temperature=0.2)

    assert result == "a reply"
    assert fake_client.chat_calls[0]["model"] == "llama3.2:latest"
    assert fake_client.chat_calls[0]["keep_alive"] == "30m"
    assert fake_client.chat_calls[0]["temperature"] == 0.2


def test_ollama_chat_backend_streams():
    backend = OllamaChatBackend(_FakeOllamaClient(), "llama3.2:latest", None)

    fragments = list(backend.chat_stream([{"role": "user", "content": "hi"}]))

    assert fragments == ["frag1", "frag2"]


def test_ollama_chat_backend_is_healthy_labels_backend():
    backend = OllamaChatBackend(_FakeOllamaClient(), "llama3.2:latest", None)

    healthy, label = backend.is_healthy()

    assert healthy is True
    assert label == "ollama"


def test_ollama_chat_backend_wraps_ollama_error():
    backend = OllamaChatBackend(_FailingOllamaClient(), "llama3.2:latest", None)

    with pytest.raises(ChatBackendError):
        backend.chat([{"role": "user", "content": "hi"}])


def test_anthropic_chat_backend_splits_system_message():
    backend = AnthropicChatBackend(api_key="sk-test", model="claude-haiku-4-5", default_max_tokens=1024)
    mock_message = MagicMock()
    mock_message.content = [MagicMock(type="text", text="hosted reply")]
    backend._client = MagicMock()
    backend._client.messages.create.return_value = mock_message

    result = backend.chat(
        [
            {"role": "system", "content": "be terse"},
            {"role": "user", "content": "hi"},
        ]
    )

    assert result == "hosted reply"
    _, kwargs = backend._client.messages.create.call_args
    assert kwargs["system"] == "be terse"
    assert kwargs["messages"] == [{"role": "user", "content": "hi"}]


def test_anthropic_chat_backend_defaults_max_tokens_when_num_predict_omitted():
    backend = AnthropicChatBackend(api_key="sk-test", model="claude-haiku-4-5", default_max_tokens=1024)
    mock_message = MagicMock()
    mock_message.content = [MagicMock(type="text", text="reply")]
    backend._client = MagicMock()
    backend._client.messages.create.return_value = mock_message

    backend.chat([{"role": "user", "content": "hi"}])

    _, kwargs = backend._client.messages.create.call_args
    assert kwargs["max_tokens"] == 1024


def test_anthropic_chat_backend_wraps_sdk_errors():
    backend = AnthropicChatBackend(api_key="sk-test", model="claude-haiku-4-5", default_max_tokens=1024)
    backend._client = MagicMock()
    backend._client.messages.create.side_effect = anthropic.APIConnectionError(request=MagicMock())

    with pytest.raises(ChatBackendError):
        backend.chat([{"role": "user", "content": "hi"}])


def test_anthropic_chat_backend_is_healthy_when_model_lookup_succeeds():
    backend = AnthropicChatBackend(api_key="sk-test", model="claude-haiku-4-5", default_max_tokens=1024)
    backend._client = MagicMock()
    backend._client.models.retrieve.return_value = MagicMock()

    healthy, label = backend.is_healthy()

    assert healthy is True
    assert label == "hosted_api"
    backend._client.models.retrieve.assert_called_once_with("claude-haiku-4-5")


def test_anthropic_chat_backend_is_unhealthy_on_api_error():
    backend = AnthropicChatBackend(api_key="sk-test", model="claude-haiku-4-5", default_max_tokens=1024)
    backend._client = MagicMock()
    backend._client.models.retrieve.side_effect = anthropic.APIConnectionError(request=MagicMock())

    healthy, label = backend.is_healthy()

    assert healthy is False
    assert label == "hosted_api"


def test_anthropic_chat_backend_is_unhealthy_on_httpx_error():
    backend = AnthropicChatBackend(api_key="sk-test", model="claude-haiku-4-5", default_max_tokens=1024)
    backend._client = MagicMock()
    backend._client.models.retrieve.side_effect = httpx.ConnectError("connection refused")

    healthy, label = backend.is_healthy()

    assert healthy is False
    assert label == "hosted_api"


def test_build_chat_backend_selects_ollama_by_default():
    backend = build_chat_backend(_config(chat_backend="ollama"), _FakeOllamaClient())

    assert isinstance(backend, OllamaChatBackend)


def test_build_chat_backend_selects_hosted_api():
    backend = build_chat_backend(
        _config(chat_backend="hosted_api", api_key="sk-real"), _FakeOllamaClient()
    )

    assert isinstance(backend, AnthropicChatBackend)


def test_build_chat_backend_fails_fast_without_api_key():
    with pytest.raises(ValueError):
        build_chat_backend(_config(chat_backend="hosted_api", api_key=None), _FakeOllamaClient())
