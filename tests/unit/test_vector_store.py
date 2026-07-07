from __future__ import annotations

import math

from src.database.vector_store import VectorStore
from src.pipeline.chunker import Chunk
from src.pipeline.embeddings import EmbeddedChunk


def _embedded(chunk_id: str, embedding: list[float]) -> EmbeddedChunk:
    chunk = Chunk(chunk_id=chunk_id, document_id="doc1", text=f"text-{chunk_id}", page_start=1, page_end=1)
    return EmbeddedChunk(chunk=chunk, embedding=embedding)


def test_identical_embedding_scores_near_one(tmp_path):
    """Regression guard: scores must be a bounded cosine similarity (~1.0 for an
    exact match), not an arbitrarily-scaled distance metric that stays near zero
    even for perfectly relevant matches (see rebuild-mvp design notes)."""
    vector_store = VectorStore(path=str(tmp_path / "vector_db"), collection_name="test")
    embedding = [1.0, 0.0, 0.0, 0.0]
    vector_store.add_chunks([_embedded("c0", embedding)])

    results = vector_store.search(embedding, top_k=1)

    assert len(results) == 1
    assert math.isclose(results[0].score, 1.0, abs_tol=1e-4)


def test_orthogonal_embedding_scores_near_zero(tmp_path):
    vector_store = VectorStore(path=str(tmp_path / "vector_db"), collection_name="test")
    vector_store.add_chunks([_embedded("c0", [1.0, 0.0, 0.0, 0.0])])

    results = vector_store.search([0.0, 1.0, 0.0, 0.0], top_k=1)

    assert len(results) == 1
    assert math.isclose(results[0].score, 0.0, abs_tol=1e-4)


def test_score_ordering_reflects_similarity(tmp_path):
    vector_store = VectorStore(path=str(tmp_path / "vector_db"), collection_name="test")
    vector_store.add_chunks(
        [
            _embedded("close", [1.0, 0.1, 0.0, 0.0]),
            _embedded("far", [0.0, 1.0, 0.0, 0.0]),
        ]
    )

    results = vector_store.search([1.0, 0.0, 0.0, 0.0], top_k=2)

    assert [r.chunk_id for r in results] == ["close", "far"]
    assert results[0].score > results[1].score


def test_get_chunks_by_document_reconstructs_chunks(tmp_path):
    vector_store = VectorStore(path=str(tmp_path / "vector_db"), collection_name="test")
    vector_store.add_chunks(
        [
            _embedded("c0", [1.0, 0.0, 0.0, 0.0]),
            _embedded("c1", [0.0, 1.0, 0.0, 0.0]),
        ]
    )

    chunks = vector_store.get_chunks_by_document("doc1")

    assert [c.chunk_id for c in chunks] == ["c0", "c1"]
    assert all(c.document_id == "doc1" for c in chunks)
    assert chunks[0].text == "text-c0"
