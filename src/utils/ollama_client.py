from __future__ import annotations

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

    def chat(self, model: str, messages: list[dict[str, str]], temperature: float = 0.7) -> str:
        """Send a chat completion request and return the assistant's reply text."""
        try:
            response = httpx.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": temperature},
                },
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
