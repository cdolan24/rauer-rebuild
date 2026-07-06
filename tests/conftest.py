from __future__ import annotations

import hashlib

import pytest


class FakeOllamaClient:
    """Deterministic stand-in for OllamaClient - no network calls."""

    def __init__(self, dim: int = 8, fail: bool = False) -> None:
        self.dim = dim
        self.fail = fail

    def embed(self, model: str, text: str) -> list[float]:
        if self.fail:
            from src.utils.ollama_client import OllamaError

            raise OllamaError("simulated embedding failure")
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [b / 255.0 for b in digest[: self.dim]]

    def chat(self, model: str, messages: list[dict[str, str]], temperature: float = 0.7) -> str:
        if self.fail:
            from src.utils.ollama_client import OllamaError

            raise OllamaError("simulated chat failure")
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return f"[fake reply to: {last_user[:50]}]"

    def is_healthy(self) -> tuple[bool, list[str]]:
        return (not self.fail), ["fake-model:latest"]


@pytest.fixture
def fake_ollama_client() -> FakeOllamaClient:
    return FakeOllamaClient()


TEST_ADMIN_PASSWORD = "test-admin-password"


def write_test_config(tmp_path, fail_ollama: bool = False) -> str:
    """Write a config.yaml pointing entirely at tmp_path, for isolated API tests."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
ollama:
  base_url: "http://localhost:0"
  chat_model: "fake-chat"
  embedding_model: "fake-embed"

chunking:
  chunk_size: 800
  chunk_overlap: 150

vector_db:
  path: "{(tmp_path / "vector_db").as_posix()}"
  collection_name: "test"

data_storage:
  path: "{(tmp_path / "data_storage.db").as_posix()}"

paths:
  data_dir: "{(tmp_path / "data").as_posix()}"
  processed_dir: "{(tmp_path / "processed").as_posix()}"

api:
  host: "0.0.0.0"
  port: 8000
  cors_origins: []

frontend:
  api_base_url: "http://localhost:8000"
  port: 7860

rag:
  # FakeOllamaClient's hash-based embeddings have no real semantic
  # relationship to query text, so cosine scores are arbitrary here -
  # don't filter on them in tests.
  min_score: 0.0

auth:
  admin_password: "{TEST_ADMIN_PASSWORD}"
""",
        encoding="utf-8",
    )
    return str(config_path)


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    import src.api.main as main_module
    from fastapi.testclient import TestClient

    config_path = write_test_config(tmp_path)
    monkeypatch.setenv("BUDDHARAUER_CONFIG", config_path)
    monkeypatch.setattr(main_module, "OllamaClient", lambda base_url, timeout=60.0: FakeOllamaClient())

    app = main_module.create_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def unhealthy_api_client(tmp_path, monkeypatch):
    import src.api.main as main_module
    from fastapi.testclient import TestClient

    config_path = write_test_config(tmp_path)
    monkeypatch.setenv("BUDDHARAUER_CONFIG", config_path)
    monkeypatch.setattr(main_module, "OllamaClient", lambda base_url, timeout=60.0: FakeOllamaClient(fail=True))

    app = main_module.create_app()
    with TestClient(app) as client:
        yield client
