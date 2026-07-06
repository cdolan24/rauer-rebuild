from __future__ import annotations

import pytest

from src.pipeline.chunker import Chunk
from src.pipeline.embeddings import EmbeddingError, embed_chunks


def _chunk(chunk_id: str) -> Chunk:
    return Chunk(chunk_id=chunk_id, document_id="doc1", text=f"text for {chunk_id}", page_start=1, page_end=1)


def test_embed_chunks_success(fake_ollama_client):
    chunks = [_chunk("c0"), _chunk("c1")]

    embedded = embed_chunks(chunks, fake_ollama_client, model="fake-embed")

    assert len(embedded) == 2
    assert embedded[0].chunk.chunk_id == "c0"
    assert len(embedded[0].embedding) == fake_ollama_client.dim
    # Same text always yields the same embedding.
    assert embedded[0].embedding != embedded[1].embedding


def test_embed_chunks_raises_on_service_failure(fake_ollama_client):
    fake_ollama_client.fail = True

    with pytest.raises(EmbeddingError):
        embed_chunks([_chunk("c0")], fake_ollama_client, model="fake-embed")
