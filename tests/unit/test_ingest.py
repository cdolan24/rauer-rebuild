from __future__ import annotations

import fitz

from src.database.document_registry import DocumentRegistry
from src.database.entity_store import EntityStore
from src.database.vector_store import VectorStore
from src.pipeline import ingest
from src.pipeline.pdf_extractor import PDFExtractionError
from src.utils.ollama_client import OllamaError


def _make_pdf(path, page_texts: list[str]) -> None:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def test_ingest_pdf_success(tmp_path, fake_ollama_client):
    pdf_path = tmp_path / "story.pdf"
    _make_pdf(pdf_path, ["Aragorn is a ranger."])
    registry = DocumentRegistry(str(tmp_path / "registry.db"))
    vector_store = VectorStore(str(tmp_path / "vector_db"), "test")

    ok = ingest.ingest_pdf(
        pdf_path, registry, vector_store, fake_ollama_client, "fake-embed", 800, 150, str(tmp_path / "processed")
    )

    assert ok is True
    record = registry.get("story")
    assert record.status == "processed"
    assert (tmp_path / "processed" / "story.txt").exists()


def test_ingest_pdf_marks_failed_on_extraction_error(tmp_path, fake_ollama_client, monkeypatch):
    pdf_path = tmp_path / "story.pdf"
    _make_pdf(pdf_path, ["text"])
    registry = DocumentRegistry(str(tmp_path / "registry.db"))
    vector_store = VectorStore(str(tmp_path / "vector_db"), "test")

    def _raise(path):
        raise PDFExtractionError("corrupted")

    monkeypatch.setattr(ingest, "extract_pdf", _raise)

    ok = ingest.ingest_pdf(
        pdf_path, registry, vector_store, fake_ollama_client, "fake-embed", 800, 150, str(tmp_path / "processed")
    )

    assert ok is False
    record = registry.get("story")
    assert record.status == "failed"
    assert "corrupted" in record.error_message


def test_ingest_pdf_succeeds_even_if_wiki_prep_fails(tmp_path, fake_ollama_client, monkeypatch):
    pdf_path = tmp_path / "story.pdf"
    _make_pdf(pdf_path, ["Aragorn is a ranger."])
    registry = DocumentRegistry(str(tmp_path / "registry.db"))
    vector_store = VectorStore(str(tmp_path / "vector_db"), "test")
    entity_store = EntityStore(str(tmp_path / "entities.db"))

    def _raise(entity_store, vector_store, ollama_client, chat_model):
        raise OllamaError("simulated dedup/summary failure")

    monkeypatch.setattr(ingest, "_prepare_wiki_data", _raise)

    ok = ingest.ingest_pdf(
        pdf_path,
        registry,
        vector_store,
        fake_ollama_client,
        "fake-embed",
        800,
        150,
        str(tmp_path / "processed"),
        entity_store=entity_store,
        chat_model="fake-chat",
    )

    assert ok is True
    assert registry.get("story").status == "processed"


def test_ingest_pdf_marks_failed_on_embedding_error(tmp_path, fake_ollama_client):
    pdf_path = tmp_path / "story.pdf"
    _make_pdf(pdf_path, ["text"])
    registry = DocumentRegistry(str(tmp_path / "registry.db"))
    vector_store = VectorStore(str(tmp_path / "vector_db"), "test")
    fake_ollama_client.fail = True

    ok = ingest.ingest_pdf(
        pdf_path, registry, vector_store, fake_ollama_client, "fake-embed", 800, 150, str(tmp_path / "processed")
    )

    assert ok is False
    record = registry.get("story")
    assert record.status == "failed"
