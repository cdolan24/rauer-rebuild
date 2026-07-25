from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.database.document_registry import DocumentRegistry
from src.database.entity_store import EntityStore
from src.database.vector_store import VectorStore
from src.pipeline.chunker import chunk_document
from src.pipeline.embeddings import EmbeddingError, embed_chunks
from src.pipeline.entity_extractor import extract_entities_for_document
from src.pipeline.image_extractor import describe_image_heavy_pages
from src.pipeline.mention_context import gather_mention_context
from src.pipeline.pdf_extractor import ExtractedDocument, PDFExtractionError, extract_pdf
from src.pipeline.relationship_extractor import extract_relationships_for_document
from src.utils.logging import get_logger
from src.utils.ollama_client import OllamaClient, OllamaError
from src.wiki.summary import generate_entity_summary

logger = get_logger(__name__)

# See entity_extractor.py's MAX_WORKERS comment: wide concurrency just queues
# chat-model calls behind each other once Ollama is serializing inference
# anyway, and each queued request's timeout clock runs the whole time it waits.
_SUMMARY_MAX_WORKERS = 3


def write_processed_text(document: ExtractedDocument, processed_dir: str) -> None:
    """Persist a document's extracted text so the API can serve it back."""
    out_dir = Path(processed_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{document.document_id}.txt"
    with out_path.open("w", encoding="utf-8") as f:
        for page in document.pages:
            f.write(f"--- page {page.page_number} ---\n{page.text}\n")


def _prepare_wiki_data(
    entity_store: EntityStore, vector_store: VectorStore, ollama_client: OllamaClient, chat_model: str
) -> None:
    """Generate a wiki summary and relationships for every entity that
    doesn't have them yet, so the wiki is fully legible immediately after
    ingestion - no separate manual summary/relationship pass needed.

    Deliberately does NOT run automatic deduplication - a real run against
    M1E's backfilled entities found the LLM-confirmation dedup step in
    entity_deduper.py had a ~40% false-positive rate on short, single-sentence
    descriptions (including one merge that looked like the safest in the
    batch but actually conflated two distinct siblings), and it ran a second
    time unreviewed during M2E's ingestion, merging 91 groups with no way to
    audit or undo it afterward. Deduplication is now a deliberate, separate
    step: run scripts/dedupe_entities.py --dry-run and review its output by
    hand before applying anything. See session notes for the M1E/M2E
    incidents; a more reliable automatic approach (e.g. grounding the
    confirmation prompt in real mention text rather than a thin one-sentence
    description) is worth revisiting later."""
    all_entities = entity_store.list_all()

    def _summarize(entity) -> None:
        mentions = entity_store.get_mentions(entity.id)
        mention_context = gather_mention_context(mentions, vector_store)
        try:
            summary = generate_entity_summary(
                entity, len(mentions), mention_context, ollama_client, chat_model
            )
        except OllamaError as e:
            logger.warning(
                "Could not generate wiki summary for entity %d (%s): %s", entity.id, entity.name, e
            )
            return
        entity_store.set_summary(entity.id, summary)

    to_summarize = [e for e in all_entities if not e.summary]
    if to_summarize:
        with ThreadPoolExecutor(max_workers=min(_SUMMARY_MAX_WORKERS, len(to_summarize))) as executor:
            list(executor.map(_summarize, to_summarize))
        logger.info("Generated %d wiki summaries", len(to_summarize))

    # Relationships, like summaries, are only generated once per entity - an
    # entity that already has at least one recorded relationship is assumed
    # done, so re-ingesting other documents doesn't keep re-querying it.
    to_relate = [e for e in all_entities if not entity_store.get_relationships(e.id)]
    if to_relate:
        extract_relationships_for_document(
            to_relate, entity_store, vector_store, ollama_client, chat_model
        )


def ingest_pdf(
    pdf_path: Path,
    registry: DocumentRegistry,
    vector_store: VectorStore,
    ollama_client: OllamaClient,
    embedding_model: str,
    chunk_size: int,
    chunk_overlap: int,
    processed_dir: str,
    entity_store: EntityStore | None = None,
    chat_model: str | None = None,
    vision_model: str | None = None,
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

    if vision_model is not None:
        try:
            document = describe_image_heavy_pages(str(pdf_path), document, ollama_client, vision_model)
        except OllamaError as e:
            # Vision description is an enhancement, not core to ingestion
            # succeeding - image-heavy pages just keep their (likely sparse)
            # extracted text if this fails.
            logger.error("Vision description failed for %s: %s", pdf_path, e)

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

    if entity_store is not None and chat_model is not None:
        try:
            # extract_entities_for_document already logs its own entity count.
            extract_entities_for_document(chunks, document_id, ollama_client, chat_model, entity_store)
        except OllamaError as e:
            # Entity tagging is an enhancement, not core to ingestion succeeding -
            # don't fail an otherwise-successful ingestion over it.
            logger.error("Entity extraction failed for %s: %s", pdf_path, e)

        try:
            _prepare_wiki_data(entity_store, vector_store, ollama_client, chat_model)
        except OllamaError as e:
            # Same reasoning - the wiki still has a lazy-generation fallback
            # for anything left unsummarized.
            logger.error("Wiki dedup/summary prep failed for %s: %s", pdf_path, e)

    return True
