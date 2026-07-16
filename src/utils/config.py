from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class OllamaConfig:
    base_url: str
    chat_model: str
    embedding_model: str
    request_timeout: float
    num_predict: int | None
    keep_alive: str | None
    # A vision-capable model (e.g. "qwen2.5vl:7b") used ONLY for pages the
    # pipeline's own heuristic flags as image-heavy - never the default for
    # anything else, and a no-op (no LLM call, no cost) for documents with
    # no flagged pages. Set to None/null to disable the feature entirely;
    # image-heavy pages then just keep whatever sparse text get_text() found.
    vision_model: str | None = "qwen2.5vl:7b"


@dataclass
class ChunkingConfig:
    chunk_size: int
    chunk_overlap: int


@dataclass
class VectorDbConfig:
    path: str
    collection_name: str


@dataclass
class PathsConfig:
    data_dir: str
    processed_dir: str


@dataclass
class ApiConfig:
    host: str
    port: int
    cors_origins: list[str]


@dataclass
class FrontendConfig:
    api_base_url: str
    port: int
    request_timeout: float
    public_url: str


@dataclass
class Config:
    ollama: OllamaConfig
    chunking: ChunkingConfig
    vector_db: VectorDbConfig
    data_storage_path: str
    paths: PathsConfig
    api: ApiConfig
    frontend: FrontendConfig
    log_level: str
    rag_min_score: float
    rag_max_history_turns: int
    admin_password: str | None
    controller_port: int
    controller_url: str


class ConfigError(Exception):
    pass


def load_config(path: str | Path = "config.yaml") -> Config:
    """Load and validate application config from a YAML file.

    Raises:
        ConfigError: if the file is missing or a required section is absent.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(
            f"Config file not found: {config_path}. Copy config.example.yaml to config.yaml."
        )

    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    def section(name: str) -> dict:
        if name not in raw:
            raise ConfigError(f"Missing required config section: '{name}'")
        return raw[name]

    ollama = section("ollama")
    chunking = section("chunking")
    vector_db = section("vector_db")
    data_storage = section("data_storage")
    paths = section("paths")
    api = section("api")
    frontend = section("frontend")

    return Config(
        ollama=OllamaConfig(
            base_url=ollama["base_url"],
            chat_model=ollama["chat_model"],
            embedding_model=ollama["embedding_model"],
            request_timeout=float(ollama.get("request_timeout", 180.0)),
            num_predict=int(ollama["num_predict"]) if ollama.get("num_predict") is not None else None,
            keep_alive=ollama.get("keep_alive"),
            # Defaults to a real model (not None) so vision kicks in
            # automatically whenever a page is actually flagged image-heavy -
            # see pipeline/image_extractor.py, which only ever calls this for
            # flagged pages and is a costless no-op for text-only documents.
            # Set explicitly to null/none in config.yaml to disable entirely.
            vision_model=ollama.get("vision_model", "qwen2.5vl:7b"),
        ),
        chunking=ChunkingConfig(
            chunk_size=int(chunking["chunk_size"]),
            chunk_overlap=int(chunking["chunk_overlap"]),
        ),
        vector_db=VectorDbConfig(
            path=vector_db["path"],
            collection_name=vector_db["collection_name"],
        ),
        data_storage_path=data_storage["path"],
        paths=PathsConfig(
            data_dir=paths["data_dir"],
            processed_dir=paths["processed_dir"],
        ),
        api=ApiConfig(
            host=api["host"],
            port=int(api["port"]),
            cors_origins=list(api.get("cors_origins", [])),
        ),
        frontend=FrontendConfig(
            api_base_url=frontend["api_base_url"],
            port=int(frontend["port"]),
            request_timeout=float(frontend.get("request_timeout", 180.0)),
            public_url=frontend.get("public_url") or f"http://localhost:{frontend['port']}",
        ),
        log_level=raw.get("logging", {}).get("level", "INFO"),
        rag_min_score=float(raw.get("rag", {}).get("min_score", 0.55)),
        rag_max_history_turns=int(raw.get("rag", {}).get("max_history_turns", 3)),
        admin_password=_resolve_admin_password(raw.get("auth", {}).get("admin_password")),
        controller_port=int(raw.get("controller", {}).get("port", 8100)),
        controller_url=raw.get("controller", {}).get("url")
        or f"http://127.0.0.1:{int(raw.get('controller', {}).get('port', 8100))}",
    )


_UNSET_ADMIN_PASSWORD_PLACEHOLDERS = {None, "", "changeme"}


def _resolve_admin_password(value: str | None) -> str | None:
    """Treat a missing/empty/placeholder password as "no password configured"
    so a forgotten config doesn't silently leave uploads open."""
    return None if value in _UNSET_ADMIN_PASSWORD_PLACEHOLDERS else value


def get_config_path() -> str:
    return os.environ.get("BUDDHARAUER_CONFIG", "config.yaml")
