from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

import anthropic
import httpx

from src.utils.config import Config
from src.utils.ollama_client import OllamaClient, OllamaError


class ChatBackendError(Exception):
    """Raised when a chat backend (Ollama or a hosted API) is unreachable or
    returns an error - a single type callers can catch regardless of which
    backend is configured."""


class ChatBackend(Protocol):
    """Chat-generation only. Embeddings and the vision model always go
    through OllamaClient directly, in every deployment profile."""

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        num_predict: int | None = None,
    ) -> str: ...

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        num_predict: int | None = None,
    ) -> Iterator[str]: ...

    def is_healthy(self) -> tuple[bool, str]: ...


class OllamaChatBackend:
    """Adapter binding the chat model/keep_alive from OllamaConfig at
    construction, so call sites no longer pass a model string per call."""

    def __init__(self, ollama_client: OllamaClient, chat_model: str, keep_alive: str | None) -> None:
        self._client = ollama_client
        self._chat_model = chat_model
        self._keep_alive = keep_alive

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        num_predict: int | None = None,
    ) -> str:
        try:
            return self._client.chat(
                self._chat_model,
                messages,
                temperature=temperature,
                num_predict=num_predict,
                keep_alive=self._keep_alive,
            )
        except OllamaError as e:
            raise ChatBackendError(str(e)) from e

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        num_predict: int | None = None,
    ) -> Iterator[str]:
        try:
            yield from self._client.chat_stream(
                self._chat_model,
                messages,
                temperature=temperature,
                num_predict=num_predict,
                keep_alive=self._keep_alive,
            )
        except OllamaError as e:
            raise ChatBackendError(str(e)) from e

    def is_healthy(self) -> tuple[bool, str]:
        healthy, _ = self._client.is_healthy()
        return healthy, "ollama"


def _split_system_message(messages: list[dict[str, str]]) -> tuple[str | None, list[dict[str, str]]]:
    """Anthropic's Messages API takes `system` as a separate top-level string,
    not a message-list entry the way Ollama's chat payload does."""
    if messages and messages[0].get("role") == "system":
        return messages[0]["content"], messages[1:]
    return None, messages


class AnthropicChatBackend:
    """Hosted-API chat backend for deployment profiles that don't want to run
    a local chat model. Embeddings/vision are unaffected - this backend is
    only ever used for chat generation."""

    def __init__(self, api_key: str, model: str, default_max_tokens: int) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._default_max_tokens = default_max_tokens

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        num_predict: int | None = None,
    ) -> str:
        system, rest = _split_system_message(messages)
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=num_predict or self._default_max_tokens,
                temperature=temperature,
                system=system if system is not None else anthropic.NOT_GIVEN,
                messages=rest,
            )
        except anthropic.APIError as e:
            raise ChatBackendError(str(e)) from e
        return next((b.text for b in response.content if b.type == "text"), "")

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        num_predict: int | None = None,
    ) -> Iterator[str]:
        system, rest = _split_system_message(messages)
        try:
            with self._client.messages.stream(
                model=self._model,
                max_tokens=num_predict or self._default_max_tokens,
                temperature=temperature,
                system=system if system is not None else anthropic.NOT_GIVEN,
                messages=rest,
            ) as stream:
                yield from stream.text_stream
        except anthropic.APIError as e:
            raise ChatBackendError(str(e)) from e

    def is_healthy(self) -> tuple[bool, str]:
        try:
            self._client.models.retrieve(self._model)
            return True, "hosted_api"
        except anthropic.APIError:
            return False, "hosted_api"
        except httpx.HTTPError:
            return False, "hosted_api"


def build_chat_backend(config: Config, ollama_client: OllamaClient) -> ChatBackend:
    if config.chat_backend == "hosted_api":
        if not config.hosted_llm.api_key:
            raise ValueError(
                "chat_backend is 'hosted_api' but hosted_llm.api_key is not set - "
                "add a real key to config.yaml before starting the app."
            )
        return AnthropicChatBackend(
            api_key=config.hosted_llm.api_key,
            model=config.hosted_llm.model,
            default_max_tokens=config.hosted_llm.max_tokens,
        )
    return OllamaChatBackend(ollama_client, config.ollama.chat_model, config.ollama.keep_alive)
