from __future__ import annotations

import json
from collections.abc import Iterator

import httpx


class OllamaError(Exception):
    """Raised when the local Ollama service is unreachable or returns an error."""


class OllamaClient:
    """Thin synchronous wrapper around Ollama's HTTP API."""

    def __init__(self, base_url: str, timeout: float = 60.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def embed(self, model: str, text: str) -> list[float]:
        """Generate an embedding vector for a piece of text."""
        try:
            response = httpx.post(
                f"{self._base_url}/api/embeddings",
                json={"model": model, "prompt": text},
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise OllamaError(f"Failed to reach Ollama embeddings endpoint: {e}") from e

        data = response.json()
        embedding = data.get("embedding")
        if not embedding:
            raise OllamaError(f"Ollama returned no embedding for model '{model}'")
        return embedding

    def _build_chat_payload(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        stream: bool,
        num_predict: int | None,
        keep_alive: str | None,
    ) -> dict:
        options = {"temperature": temperature}
        if num_predict is not None:
            options["num_predict"] = num_predict
        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": options,
        }
        if keep_alive is not None:
            payload["keep_alive"] = keep_alive
        return payload

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        num_predict: int | None = None,
        keep_alive: str | None = None,
    ) -> str:
        """Send a chat completion request and return the assistant's reply text."""
        payload = self._build_chat_payload(model, messages, temperature, False, num_predict, keep_alive)
        try:
            response = httpx.post(
                f"{self._base_url}/api/chat",
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise OllamaError(f"Failed to reach Ollama chat endpoint: {e}") from e

        data = response.json()
        message = data.get("message", {})
        content = message.get("content")
        if content is None:
            raise OllamaError(f"Ollama returned no message content for model '{model}'")
        return content

    def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        num_predict: int | None = None,
        keep_alive: str | None = None,
    ) -> Iterator[str]:
        """Stream a chat completion, yielding content fragments as they arrive.

        Ollama's streaming response is newline-delimited JSON, one object per
        fragment, the last one carrying "done": true.
        """
        payload = self._build_chat_payload(model, messages, temperature, True, num_predict, keep_alive)
        try:
            with httpx.stream(
                "POST", f"{self._base_url}/api/chat", json=payload, timeout=self._timeout
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data.get("done"):
                        break
        except httpx.HTTPError as e:
            raise OllamaError(f"Failed to reach Ollama chat endpoint (stream): {e}") from e

    def is_healthy(self) -> tuple[bool, list[str]]:
        """Check connectivity and return (is_healthy, loaded_model_names)."""
        try:
            response = httpx.get(f"{self._base_url}/api/tags", timeout=5.0)
            response.raise_for_status()
        except httpx.HTTPError:
            return False, []

        data = response.json()
        models = [m.get("name", "") for m in data.get("models", [])]
        return True, models
