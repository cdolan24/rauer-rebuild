from __future__ import annotations

from src.database.vector_store import VectorStore
from src.pipeline.chunker import Chunk
from src.pipeline.embeddings import EmbeddedChunk
from src.rag.retriever import Retriever


def test_retriever_returns_relevant_chunks(tmp_path, fake_ollama_client):
    vector_store = VectorStore(path=str(tmp_path / "vector_db"), collection_name="test")
    chunks = [
        Chunk(chunk_id="c0", document_id="doc1", text="Aragorn is a ranger.", page_start=1, page_end=1),
        Chunk(chunk_id="c1", document_id="doc1", text="Bree is a small town.", page_start=2, page_end=2),
    ]
    embedded = [
        EmbeddedChunk(chunk=c, embedding=fake_ollama_client.embed("fake-embed", c.text)) for c in chunks
    ]
    vector_store.add_chunks(embedded)

    retriever = Retriever(vector_store, fake_ollama_client, embedding_model="fake-embed")
    results = retriever.retrieve("Who is Aragorn?", top_k=1)

    assert len(results) == 1
    assert results[0].document_id == "doc1"


def test_retriever_empty_store_returns_no_results(tmp_path, fake_ollama_client):
    vector_store = VectorStore(path=str(tmp_path / "vector_db"), collection_name="test")
    retriever = Retriever(vector_store, fake_ollama_client, embedding_model="fake-embed")

    results = retriever.retrieve("anything", top_k=5)

    assert results == []
