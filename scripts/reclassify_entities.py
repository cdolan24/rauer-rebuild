#!/usr/bin/env python
"""One-off CLI to reclassify existing entities into the expanded taxonomy.

Works from each entity's stored name/description - no source document
re-reading, no re-running extraction. Safe to re-run (a plain overwrite via
EntityStore.set_type, not additive).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.entity_store import EntityStore
from src.pipeline.entity_extractor import reclassify_entities
from src.utils.config import load_config
from src.utils.logging import get_logger, setup_logging
from src.utils.ollama_client import OllamaClient

logger = get_logger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config.log_level)

    ollama_client = OllamaClient(config.ollama.base_url, timeout=config.ollama.request_timeout)
    entity_store = EntityStore(config.data_storage_path)

    entities = entity_store.list_all()
    if not entities:
        logger.warning("No entities found to reclassify.")
        return 0

    logger.info("Reclassifying %d entities...", len(entities))
    updates = reclassify_entities(entities, ollama_client, config.ollama.chat_model)

    for entity_id, new_type in updates.items():
        entity_store.set_type(entity_id, new_type)

    logger.info(
        "Reclassified %d/%d entities (%d unchanged)",
        len(updates), len(entities), len(entities) - len(updates),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
