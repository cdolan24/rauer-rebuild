from __future__ import annotations

from dataclasses import dataclass

import chromadb

from src.pipeline.chunker import Chunk
from src.pipeline.embeddings import EmbeddedChunk


@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    text: str
    page_start: int
    page_end: int
    score: float
    source_type: str = "text"  # "text" (directly extracted) or "visual" (vision-model description)


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
                    "source_type": ec.chunk.source_type,
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
                    # .get() with a default: chunks stored before this field
                    # existed won't have it in their metadata.
                    source_type=metadata.get("source_type", "text"),
                )
            )
        return results

    def count(self) -> int:
        return self._collection.count()

    def get_chunks_by_document(self, document_id: str) -> list[Chunk]:
        """Reconstruct a document's chunks from the store (e.g. for re-running
        entity extraction on an already-ingested document)."""
        result = self._collection.get(where={"document_id": document_id})
        chunks = [
            Chunk(
                chunk_id=chunk_id,
                document_id=metadata["document_id"],
                text=text,
                page_start=metadata["page_start"],
                page_end=metadata["page_end"],
                source_type=metadata.get("source_type", "text"),
            )
            for chunk_id, text, metadata in zip(
                result["ids"], result["documents"], result["metadatas"]
            )
        ]
        chunks.sort(key=lambda c: c.chunk_id)
        return chunks
