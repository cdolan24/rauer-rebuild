#!/usr/bin/env python
"""CLI to (re-)run relationship extraction for already-extracted entities."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.entity_store import EntityStore
from src.database.vector_store import VectorStore
from src.pipeline.relationship_extractor import extract_relationships_for_document
from src.utils.config import load_config
from src.utils.logging import get_logger, setup_logging
from src.utils.ollama_client import OllamaClient

logger = get_logger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "document_id",
        nargs="?",
        help="Extract relationships for one document's entities instead of every entity in the store",
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config.log_level)

    ollama_client = OllamaClient(config.ollama.base_url, timeout=config.ollama.request_timeout)
    entity_store = EntityStore(config.data_storage_path)
    vector_store = VectorStore(config.vector_db.path, config.vector_db.collection_name)

    if args.document_id:
        entities = entity_store.list_by_document(args.document_id)
    else:
        entities = entity_store.list_all()

    if not entities:
        logger.warning("No entities found to extract relationships for.")
        return 0

    count = extract_relationships_for_document(
        entities, entity_store, vector_store, ollama_client, config.ollama.chat_model
    )
    logger.info("Extracted %d relationship(s) for %d entities.", count, len(entities))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
