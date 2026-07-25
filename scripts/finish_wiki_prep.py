#!/usr/bin/env python
"""One-off resume script: finish wiki-data prep (summaries + relationships)
for any entities left over from an interrupted ingestion run.

_prepare_wiki_data only touches entities missing a summary or relationships,
so this is safe to run any time without duplicating M1E's already-complete
data or re-touching M2E's already-extracted entities/chunks.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.entity_store import EntityStore
from src.database.vector_store import VectorStore
from src.pipeline.ingest import _prepare_wiki_data
from src.utils.config import load_config
from src.utils.logging import get_logger, setup_logging
from src.utils.ollama_client import OllamaClient

logger = get_logger(__name__)


def main() -> int:
    config = load_config("config.yaml")
    setup_logging(config.log_level)

    ollama_client = OllamaClient(config.ollama.base_url, timeout=config.ollama.request_timeout)
    entity_store = EntityStore(config.data_storage_path)
    vector_store = VectorStore(config.vector_db.path, config.vector_db.collection_name)

    _prepare_wiki_data(entity_store, vector_store, ollama_client, config.ollama.chat_model)
    logger.info("Wiki data prep resume complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
