from __future__ import annotations

import fitz

from src.database.document_registry import DocumentRegistry
from src.database.vector_store import VectorStore
from src.pipeline.chunker import chunk_document
from src.pipeline.embeddings import embed_chunks
from src.pipeline.pdf_extractor import extract_pdf


def _make_pdf(path, page_texts: list[str]) -> None:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def test_full_ingestion_pipeline(tmp_path, fake_ollama_client):
    pdf_path = tmp_path / "test_story.pdf"
    _make_pdf(
        pdf_path,
        [
            "Aragorn is a ranger who protects the northern borders.",
            "Bree is a small town where travelers meet at the inn.",
        ],
    )

    document = extract_pdf(pdf_path)
    chunks = chunk_document(document, chunk_size=800, chunk_overlap=150)
    assert len(chunks) > 0

    embedded = embed_chunks(chunks, fake_ollama_client, model="fake-embed")

    vector_store = VectorStore(path=str(tmp_path / "vector_db"), collection_name="test")
    vector_store.add_chunks(embedded)
    assert vector_store.count() == len(chunks)

    registry = DocumentRegistry(str(tmp_path / "registry.db"))
    registry.mark_processed(
        document.document_id, document.title, str(pdf_path), document.page_count, len(chunks)
    )

    record = registry.get(document.document_id)
    assert record is not None
    assert record.status == "processed"
    assert record.chunk_count == len(chunks)

    query_embedding = fake_ollama_client.embed("fake-embed", "Who is Aragorn?")
    results = vector_store.search(query_embedding, top_k=2)
    assert len(results) > 0
    assert all(r.document_id == document.document_id for r in results)
