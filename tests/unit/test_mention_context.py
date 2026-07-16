from __future__ import annotations

from src.database.entity_store import EntityMention
from src.pipeline.chunker import Chunk
from src.pipeline.mention_context import gather_mention_context


class FakeVectorStore:
    """Returns pre-seeded chunks for a document, tracking call count so tests
    can assert chunks are fetched once per document, not once per mention."""

    def __init__(self, chunks_by_document: dict[str, list[Chunk]]) -> None:
        self._chunks_by_document = chunks_by_document
        self.calls: list[str] = []

    def get_chunks_by_document(self, document_id: str) -> list[Chunk]:
        self.calls.append(document_id)
        return self._chunks_by_document.get(document_id, [])


def _chunk(chunk_id, document_id, text, page=1):
    return Chunk(chunk_id=chunk_id, document_id=document_id, text=text, page_start=page, page_end=page)


def test_gather_mention_context_empty_for_no_mentions():
    store = FakeVectorStore({})
    assert gather_mention_context([], store) == ""


def test_gather_mention_context_fetches_document_once_for_multiple_mentions():
    store = FakeVectorStore(
        {"doc1": [_chunk("c0", "doc1", "First sighting."), _chunk("c1", "doc1", "Second sighting.")]}
    )
    mentions = [
        EntityMention(entity_id=1, chunk_id="c0", document_id="doc1", page_start=1, page_end=1),
        EntityMention(entity_id=1, chunk_id="c1", document_id="doc1", page_start=2, page_end=2),
    ]

    context = gather_mention_context(mentions, store)

    assert "First sighting." in context
    assert "Second sighting." in context
    assert store.calls == ["doc1"]  # fetched once, not once per mention


def test_gather_mention_context_spans_multiple_documents():
    store = FakeVectorStore(
        {
            "doc1": [_chunk("c0", "doc1", "In M1E.")],
            "doc2": [_chunk("c0", "doc2", "In M2E.")],
        }
    )
    mentions = [
        EntityMention(entity_id=1, chunk_id="c0", document_id="doc1", page_start=1, page_end=1),
        EntityMention(entity_id=1, chunk_id="c0", document_id="doc2", page_start=1, page_end=1),
    ]

    context = gather_mention_context(mentions, store)

    assert "In M1E." in context
    assert "In M2E." in context


def test_gather_mention_context_caps_by_max_mentions():
    chunks = [_chunk(f"c{i}", "doc1", f"Sighting {i}.") for i in range(10)]
    store = FakeVectorStore({"doc1": chunks})
    mentions = [
        EntityMention(entity_id=1, chunk_id=c.chunk_id, document_id="doc1", page_start=1, page_end=1)
        for c in chunks
    ]

    context = gather_mention_context(mentions, store, max_mentions=3)

    assert len([line for line in context.split("\n\n") if line]) == 3


def test_gather_mention_context_caps_by_max_chars():
    chunks = [_chunk(f"c{i}", "doc1", "x" * 100) for i in range(10)]
    store = FakeVectorStore({"doc1": chunks})
    mentions = [
        EntityMention(entity_id=1, chunk_id=c.chunk_id, document_id="doc1", page_start=1, page_end=1)
        for c in chunks
    ]

    context = gather_mention_context(mentions, store, max_chars=250)

    assert len(context) < 400  # stopped well short of all 1000 chars


def test_gather_mention_context_skips_mentions_missing_from_the_store():
    store = FakeVectorStore({"doc1": [_chunk("c0", "doc1", "Only this one exists.")]})
    mentions = [
        EntityMention(entity_id=1, chunk_id="c0", document_id="doc1", page_start=1, page_end=1),
        EntityMention(entity_id=1, chunk_id="missing", document_id="doc1", page_start=2, page_end=2),
    ]

    context = gather_mention_context(mentions, store)

    assert context == "Only this one exists."
