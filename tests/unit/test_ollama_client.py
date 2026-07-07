from __future__ import annotations

import httpx
import pytest

from src.utils.ollama_client import OllamaClient, OllamaError


class _FakeResponse:
    def __init__(self, json_data: dict, status_code: int = 200) -> None:
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self) -> dict:
        return self._json_data


def test_embed_success(monkeypatch):
    monkeypatch.setattr(
        httpx, "post", lambda *a, **kw: _FakeResponse({"embedding": [0.1, 0.2, 0.3]})
    )
    client = OllamaClient("http://localhost:11434")

    result = client.embed("nomic-embed-text", "hello")

    assert result == [0.1, 0.2, 0.3]


def test_embed_raises_on_connection_error(monkeypatch):
    def _raise(*a, **kw):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", _raise)
    client = OllamaClient("http://localhost:11434")

    with pytest.raises(OllamaError):
        client.embed("nomic-embed-text", "hello")


def test_embed_raises_on_missing_embedding_field(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: _FakeResponse({}))
    client = OllamaClient("http://localhost:11434")

    with pytest.raises(OllamaError):
        client.embed("nomic-embed-text", "hello")


def test_chat_success(monkeypatch):
    monkeypatch.setattr(
        httpx, "post", lambda *a, **kw: _FakeResponse({"message": {"content": "hi there"}})
    )
    client = OllamaClient("http://localhost:11434")

    result = client.chat("llama3.2", [{"role": "user", "content": "hello"}])

    assert result == "hi there"


def test_chat_raises_on_connection_error(monkeypatch):
    def _raise(*a, **kw):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", _raise)
    client = OllamaClient("http://localhost:11434")

    with pytest.raises(OllamaError):
        client.chat("llama3.2", [{"role": "user", "content": "hello"}])


def test_is_healthy_true_when_reachable(monkeypatch):
    monkeypatch.setattr(
        httpx, "get", lambda *a, **kw: _FakeResponse({"models": [{"name": "llama3.2:latest"}]})
    )
    client = OllamaClient("http://localhost:11434")

    healthy, models = client.is_healthy()

    assert healthy is True
    assert models == ["llama3.2:latest"]


def test_is_healthy_false_when_unreachable(monkeypatch):
    def _raise(*a, **kw):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "get", _raise)
    client = OllamaClient("http://localhost:11434")

    healthy, models = client.is_healthy()

    assert healthy is False
    assert models == []


def test_chat_includes_num_predict_and_keep_alive_when_given(monkeypatch):
    captured = {}

    def _post(url, json, **kw):
        captured.update(json)
        return _FakeResponse({"message": {"content": "hi"}})

    monkeypatch.setattr(httpx, "post", _post)
    client = OllamaClient("http://localhost:11434")

    client.chat("llama3.2", [{"role": "user", "content": "hi"}], num_predict=256, keep_alive="30m")

    assert captured["options"]["num_predict"] == 256
    assert captured["keep_alive"] == "30m"


class _FakeStreamResponse:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    def raise_for_status(self) -> None:
        pass

    def iter_lines(self):
        return iter(self._lines)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def test_chat_stream_yields_fragments_in_order(monkeypatch):
    lines = [
        '{"message": {"content": "Hel"}, "done": false}',
        '{"message": {"content": "lo"}, "done": false}',
        '{"message": {"content": ""}, "done": true}',
    ]
    monkeypatch.setattr(httpx, "stream", lambda *a, **kw: _FakeStreamResponse(lines))
    client = OllamaClient("http://localhost:11434")

    fragments = list(client.chat_stream("llama3.2", [{"role": "user", "content": "hi"}]))

    assert fragments == ["Hel", "lo"]


def test_chat_stream_skips_blank_lines(monkeypatch):
    lines = [
        "",
        '{"message": {"content": "ok"}, "done": true}',
    ]
    monkeypatch.setattr(httpx, "stream", lambda *a, **kw: _FakeStreamResponse(lines))
    client = OllamaClient("http://localhost:11434")

    fragments = list(client.chat_stream("llama3.2", [{"role": "user", "content": "hi"}]))

    assert fragments == ["ok"]


def test_chat_stream_raises_on_connection_error(monkeypatch):
    def _raise(*a, **kw):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "stream", _raise)
    client = OllamaClient("http://localhost:11434")

    with pytest.raises(OllamaError):
        list(client.chat_stream("llama3.2", [{"role": "user", "content": "hi"}]))
