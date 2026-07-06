from __future__ import annotations

from src.pipeline.chunker import chunk_document
from src.pipeline.pdf_extractor import ExtractedDocument, ExtractedPage


def _doc(pages: list[str]) -> ExtractedDocument:
    return ExtractedDocument(
        document_id="doc1",
        title="doc1",
        source_path="doc1.pdf",
        pages=[ExtractedPage(page_number=i + 1, text=t) for i, t in enumerate(pages)],
    )


def test_chunk_metadata_complete():
    document = _doc(["Aragorn walked into Bree.\n\nHe met Gandalf there."])

    chunks = chunk_document(document, chunk_size=800, chunk_overlap=150)

    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.chunk_id.startswith("doc1_chunk_")
        assert chunk.document_id == "doc1"
        assert chunk.page_start == 1
        assert chunk.page_end == 1
        assert chunk.text


def test_chunk_ids_are_unique():
    long_paragraph = " ".join(f"Sentence number {i} about Malifaux lore." for i in range(200))
    document = _doc([long_paragraph])

    chunks = chunk_document(document, chunk_size=200, chunk_overlap=50)

    assert len(chunks) > 1
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))


def test_chunk_overlap_preserves_context():
    long_paragraph = " ".join(f"Sentence number {i} about Malifaux lore." for i in range(200))
    document = _doc([long_paragraph])

    chunks = chunk_document(document, chunk_size=200, chunk_overlap=50)

    assert len(chunks) > 1
    # Consecutive chunks should share at least some text due to overlap.
    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    assert set(first_words[-5:]) & set(second_words[:10])


def test_chunk_spans_multiple_pages():
    document = _doc(["Short page one text.", "Short page two text."])

    chunks = chunk_document(document, chunk_size=800, chunk_overlap=150)

    # Both pages are small enough to combine into a single chunk spanning both.
    assert any(c.page_start == 1 and c.page_end == 2 for c in chunks)


def test_empty_document_returns_no_chunks():
    document = _doc(["", "   "])

    chunks = chunk_document(document)

    assert chunks == []
