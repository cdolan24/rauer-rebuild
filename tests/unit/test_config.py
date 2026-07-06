from __future__ import annotations

import pytest

from src.utils.config import ConfigError, load_config

_BASE_CONFIG = """
ollama:
  base_url: "http://localhost:11434"
  chat_model: "llama3.2:latest"
  embedding_model: "nomic-embed-text:latest"

chunking:
  chunk_size: 800
  chunk_overlap: 150

vector_db:
  path: "./vector_db"
  collection_name: "test"

data_storage:
  path: "./data_storage/db.sqlite"

paths:
  data_dir: "./data"
  processed_dir: "./processed"

api:
  host: "0.0.0.0"
  port: 8000
  cors_origins: []

frontend:
  api_base_url: "http://localhost:8000"
  port: 7860
"""


def test_missing_config_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "does_not_exist.yaml")


def test_rag_min_score_defaults_when_section_absent(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(_BASE_CONFIG, encoding="utf-8")

    config = load_config(config_path)

    assert config.rag_min_score == 0.55


def test_rag_min_score_can_be_overridden(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(_BASE_CONFIG + "\nrag:\n  min_score: 0.3\n", encoding="utf-8")

    config = load_config(config_path)

    assert config.rag_min_score == 0.3


def test_missing_required_section_raises(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("ollama:\n  base_url: x\n  chat_model: y\n  embedding_model: z\n", encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(config_path)
