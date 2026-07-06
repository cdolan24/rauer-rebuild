from __future__ import annotations

from dataclasses import dataclass

import chromadb

from src.pipeline.embeddings import EmbeddedChunk


@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    text: str
    page_start: int
    page_end: int
    score: float


class VectorStore:
    """Local persistent vector store backed by ChromaDB.

    Kept behind this narrow interface (add_chunks/search) so the backing
    store can be swapped (e.g. for Qdrant) without touching ingestion or RAG code.
    """

    def __init__(self, path: str, collection_name: str) -> None:
        self._client = chromadb.PersistentClient(path=path)
        self._collection = self._client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(self, embedded_chunks: list[EmbeddedChunk]) -> None:
        if not embedded_chunks:
            return

        self._collection.upsert(
            ids=[ec.chunk.chunk_id for ec in embedded_chunks],
            embeddings=[ec.embedding for ec in embedded_chunks],
            documents=[ec.chunk.text for ec in embedded_chunks],
            metadatas=[
                {
                    "document_id": ec.chunk.document_id,
                    "page_start": ec.chunk.page_start,
                    "page_end": ec.chunk.page_end,
                }
                for ec in embedded_chunks
            ],
        )

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[SearchResult]:
        if self._collection.count() == 0:
            return []

        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self._collection.count()),
        )

        results: list[SearchResult] = []
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
            # With hnsw:space="cosine", Chroma's distance is (1 - cosine similarity),
            # so this recovers cosine similarity directly: bounded, 1.0 = identical direction.
            score = 1.0 - distance
            results.append(
                SearchResult(
                    chunk_id=chunk_id,
                    document_id=metadata["document_id"],
                    text=text,
                    page_start=metadata["page_start"],
                    page_end=metadata["page_end"],
                    score=score,
                )
            )
        return results

    def count(self) -> int:
        return self._collection.count()
