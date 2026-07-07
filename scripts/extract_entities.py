#!/usr/bin/env python
"""CLI to (re-)run entity extraction for already-ingested documents."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.document_registry import DocumentRegistry
from src.database.entity_store import EntityStore
from src.database.vector_store import VectorStore
from src.pipeline.entity_extractor import extract_entities_for_document
from src.utils.config import load_config
from src.utils.logging import get_logger, setup_logging
from src.utils.ollama_client import OllamaClient

logger = get_logger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document_id", nargs="?", help="Extract entities for a single document id instead of all processed documents")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config.log_level)

    ollama_client = OllamaClient(config.ollama.base_url, timeout=config.ollama.request_timeout)
    registry = DocumentRegistry(config.data_storage_path)
    vector_store = VectorStore(config.vector_db.path, config.vector_db.collection_name)
    entity_store = EntityStore(config.data_storage_path)

    if args.document_id:
        document_ids = [args.document_id]
    else:
        document_ids = [r.document_id for r in registry.list_all() if r.status == "processed"]

    if not document_ids:
        logger.warning("No processed documents found to extract entities from.")
        return 0

    for document_id in document_ids:
        chunks = vector_store.get_chunks_by_document(document_id)
        if not chunks:
            logger.warning("No chunks found for %s, skipping.", document_id)
            continue
        count = extract_entities_for_document(
            chunks, document_id, ollama_client, config.ollama.chat_model, entity_store
        )
        logger.info("Extracted %d entities for %s (%d chunks)", count, document_id, len(chunks))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
