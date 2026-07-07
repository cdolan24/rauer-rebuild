from __future__ import annotations

from pathlib import Path

from src.database.document_registry import DocumentRegistry
from src.database.vector_store import VectorStore
from src.pipeline.chunker import chunk_document
from src.pipeline.embeddings import EmbeddingError, embed_chunks
from src.pipeline.pdf_extractor import ExtractedDocument, PDFExtractionError, extract_pdf
from src.utils.logging import get_logger
from src.utils.ollama_client import OllamaClient

logger = get_logger(__name__)


def write_processed_text(document: ExtractedDocument, processed_dir: str) -> None:
    """Persist a document's extracted text so the API can serve it back."""
    out_dir = Path(processed_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{document.document_id}.txt"
    with out_path.open("w", encoding="utf-8") as f:
        for page in document.pages:
            f.write(f"--- page {page.page_number} ---\n{page.text}\n")


def ingest_pdf(
    pdf_path: Path,
    registry: DocumentRegistry,
    vector_store: VectorStore,
    ollama_client: OllamaClient,
    embedding_model: str,
    chunk_size: int,
    chunk_overlap: int,
    processed_dir: str,
) -> bool:
    """Run the full ingestion pipeline for a single PDF. Returns True on success."""
    document_id = pdf_path.stem
    registry.mark_pending(document_id, pdf_path.stem, str(pdf_path))

    try:
        document = extract_pdf(pdf_path)
    except PDFExtractionError as e:
        logger.error("Extraction failed for %s: %s", pdf_path, e)
        registry.mark_failed(document_id, pdf_path.stem, str(pdf_path), str(e))
        return False

    chunks = chunk_document(document, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    try:
        embedded = embed_chunks(chunks, ollama_client, embedding_model)
    except EmbeddingError as e:
        logger.error("Embedding failed for %s: %s", pdf_path, e)
        registry.mark_failed(document_id, pdf_path.stem, str(pdf_path), str(e))
        return False

    vector_store.add_chunks(embedded)
    write_processed_text(document, processed_dir)
    registry.mark_processed(
        document_id, pdf_path.stem, str(pdf_path), document.page_count, len(chunks)
    )
    logger.info(
        "Processed %s: %d pages, %d chunks", pdf_path.name, document.page_count, len(chunks)
    )
    return True
