from __future__ import annotations

from src.database.vector_store import SearchResult, VectorStore
from src.utils.ollama_client import OllamaClient


class Retriever:
    """Embeds a query and searches the vector store for relevant chunks."""

    def __init__(self, vector_store: VectorStore, ollama_client: OllamaClient, embedding_model: str) -> None:
        self._vector_store = vector_store
        self._ollama_client = ollama_client
        self._embedding_model = embedding_model

    def retrieve(self, query: str, top_k: int = 5) -> list[SearchResult]:
        query_embedding = self._ollama_client.embed(self._embedding_model, query)
        return self._vector_store.search(query_embedding, top_k=top_k)
