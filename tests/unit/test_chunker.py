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


def _doc_with_sections(pages: list[tuple[str, str | None]]) -> ExtractedDocument:
    return ExtractedDocument(
        document_id="doc1",
        title="doc1",
        source_path="doc1.pdf",
        pages=[
            ExtractedPage(page_number=i + 1, text=text, section=section)
            for i, (text, section) in enumerate(pages)
        ],
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


def test_section_change_forces_a_hard_break():
    # Small enough to combine into one chunk by size alone, but they belong
    # to two different detected stories - should NOT be merged.
    document = _doc_with_sections(
        [
            ("The end of the first story.", "Snow on a Tombstone"),
            ("The start of the second story.", "Into the Breach"),
        ]
    )

    chunks = chunk_document(document, chunk_size=800, chunk_overlap=150)

    assert len(chunks) == 2
    assert "first story" in chunks[0].text
    assert "second story" in chunks[1].text
    assert "second story" not in chunks[0].text
    assert "first story" not in chunks[1].text


def test_pages_without_detected_section_still_merge_by_size():
    # None sections (typical for rules-heavy content) shouldn't force a
    # break - regular size-based merging still applies.
    document = _doc_with_sections(
        [("Short page one text.", None), ("Short page two text.", None)]
    )

    chunks = chunk_document(document, chunk_size=800, chunk_overlap=150)

    assert any(c.page_start == 1 and c.page_end == 2 for c in chunks)


def test_section_boundary_does_not_carry_overlap_across_it():
    long_paragraph = " ".join(f"Sentence number {i} about the first story." for i in range(60))
    document = _doc_with_sections(
        [
            (long_paragraph, "Snow on a Tombstone"),
            ("The second story begins here.", "Into the Breach"),
        ]
    )

    chunks = chunk_document(document, chunk_size=200, chunk_overlap=50)

    assert len(chunks) >= 2
    last_of_first_story = chunks[-2]
    first_of_second_story = chunks[-1]
    assert "second story begins" in first_of_second_story.text
    assert "first story" not in first_of_second_story.text
    assert last_of_first_story.text != first_of_second_story.text
