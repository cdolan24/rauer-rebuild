#!/usr/bin/env python
"""CLI to ingest PDFs from the data directory into the vector database."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.database.document_registry import DocumentRegistry
from src.database.vector_store import VectorStore
from src.pipeline.ingest import ingest_pdf
from src.utils.config import load_config
from src.utils.logging import get_logger, setup_logging
from src.utils.ollama_client import OllamaClient

logger = get_logger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", help="Process a single PDF instead of the whole data dir")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config.log_level)

    ollama_client = OllamaClient(config.ollama.base_url, timeout=config.ollama.request_timeout)
    registry = DocumentRegistry(config.data_storage_path)
    vector_store = VectorStore(config.vector_db.path, config.vector_db.collection_name)

    if args.file:
        pdf_paths = [Path(args.file)]
    else:
        pdf_paths = sorted(Path(config.paths.data_dir).glob("*.pdf"))

    if not pdf_paths:
        logger.warning("No PDF files found to process.")
        return 0

    succeeded = 0
    failed = 0
    for pdf_path in pdf_paths:
        ok = ingest_pdf(
            pdf_path,
            registry,
            vector_store,
            ollama_client,
            config.ollama.embedding_model,
            config.chunking.chunk_size,
            config.chunking.chunk_overlap,
            config.paths.processed_dir,
        )
        succeeded += int(ok)
        failed += int(not ok)

    logger.info("Done. %d succeeded, %d failed.", succeeded, failed)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
