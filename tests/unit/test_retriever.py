from __future__ import annotations

from src.database.entity_store import EntityMention, EntityStore
from src.database.vector_store import VectorStore
from src.pipeline.chunker import Chunk
from src.pipeline.embeddings import EmbeddedChunk
from src.rag.retriever import Retriever


class _FixedEmbedClient:
    """Returns the same embedding for any query - lets tests control ranking precisely."""

    def __init__(self, embedding: list[float]) -> None:
        self.embedding = embedding

    def embed(self, model, text):
        return self.embedding


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


def test_entity_boost_promotes_tagged_chunk_above_higher_raw_similarity(tmp_path):
    vector_store = VectorStore(path=str(tmp_path / "vector_db"), collection_name="test")
    query_embedding = [1.0, 0.0, 0.0, 0.0]

    # "other" is a closer raw cosine match to the query than "target".
    vector_store.add_chunks(
        [
            EmbeddedChunk(
                chunk=Chunk(chunk_id="other", document_id="doc1", text="unrelated text", page_start=1, page_end=1),
                embedding=[0.95, 0.05, 0.0, 0.0],
            ),
            EmbeddedChunk(
                chunk=Chunk(chunk_id="target", document_id="doc1", text="Lady Justice appears here.", page_start=2, page_end=2),
                embedding=[0.80, 0.20, 0.0, 0.0],
            ),
        ]
    )

    entity_store = EntityStore(str(tmp_path / "entities.db"))
    entity_id = entity_store.add_entity("doc1", "Lady Justice", "character", "desc")
    entity_store.add_mentions(
        [EntityMention(entity_id=entity_id, chunk_id="target", document_id="doc1", page_start=2, page_end=2)]
    )

    retriever = Retriever(
        vector_store, _FixedEmbedClient(query_embedding), embedding_model="fake-embed", entity_store=entity_store
    )

    # Without the boost, "other" would rank first (higher raw cosine similarity).
    unboosted = Retriever(vector_store, _FixedEmbedClient(query_embedding), embedding_model="fake-embed")
    unboosted_results = unboosted.retrieve("Who is Lady Justice?", top_k=2)
    assert unboosted_results[0].chunk_id == "other"

    boosted_results = retriever.retrieve("Who is Lady Justice?", top_k=2)
    assert boosted_results[0].chunk_id == "target"


def test_entity_boost_does_not_affect_query_without_known_entity(tmp_path):
    vector_store = VectorStore(path=str(tmp_path / "vector_db"), collection_name="test")
    query_embedding = [1.0, 0.0, 0.0, 0.0]
    vector_store.add_chunks(
        [
            EmbeddedChunk(
                chunk=Chunk(chunk_id="other", document_id="doc1", text="unrelated text", page_start=1, page_end=1),
                embedding=[0.95, 0.05, 0.0, 0.0],
            ),
            EmbeddedChunk(
                chunk=Chunk(chunk_id="target", document_id="doc1", text="Lady Justice appears here.", page_start=2, page_end=2),
                embedding=[0.80, 0.20, 0.0, 0.0],
            ),
        ]
    )

    entity_store = EntityStore(str(tmp_path / "entities.db"))
    entity_id = entity_store.add_entity("doc1", "Lady Justice", "character", "desc")
    entity_store.add_mentions(
        [EntityMention(entity_id=entity_id, chunk_id="target", document_id="doc1", page_start=2, page_end=2)]
    )

    retriever = Retriever(
        vector_store, _FixedEmbedClient(query_embedding), embedding_model="fake-embed", entity_store=entity_store
    )

    results = retriever.retrieve("What's the weather like?", top_k=2)

    assert results[0].chunk_id == "other"
