#!/usr/bin/env python
"""One-off CLI to merge duplicate entities (the same underlying entity under
different name variants) using an LLM-assisted pass over stored
name/description - no source document re-reading.

Use --dry-run to preview merge groups before applying them; merging deletes
rows, so review the dry-run output (and back up the database) before running
for real.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.entity_store import EntityStore
from src.pipeline.entity_deduper import find_duplicate_groups
from src.utils.config import load_config
from src.utils.logging import get_logger, setup_logging
from src.utils.ollama_client import OllamaClient

logger = get_logger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print merge groups without applying them"
    )
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config.log_level)

    ollama_client = OllamaClient(config.ollama.base_url, timeout=config.ollama.request_timeout)
    entity_store = EntityStore(config.data_storage_path)

    entities = entity_store.list_all()
    if not entities:
        logger.warning("No entities found.")
        return 0

    by_id = {e.id: e for e in entities}
    logger.info("Scanning %d entities for duplicates...", len(entities))
    groups = find_duplicate_groups(entities, ollama_client, config.ollama.chat_model)

    if not groups:
        logger.info("No duplicate groups found.")
        return 0

    for group in groups:
        keep = by_id[group.keep_id]
        merged_names = [by_id[m].name for m in group.merge_ids]
        logger.info("Merge: keep '%s' (id=%d) <- %s", keep.name, keep.id, merged_names)

    if args.dry_run:
        logger.info("Dry run - no changes applied. %d merge group(s) found.", len(groups))
        return 0

    for group in groups:
        entity_store.merge_entities(group.keep_id, group.merge_ids)

    total_merged = sum(len(g.merge_ids) for g in groups)
    logger.info("Merged %d duplicate entities into %d groups.", total_merged, len(groups))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
