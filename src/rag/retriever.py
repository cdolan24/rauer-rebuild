from __future__ import annotations

from src.database.entity_store import EntityStore
from src.database.vector_store import SearchResult, VectorStore
from src.utils.ollama_client import OllamaClient

ENTITY_BOOST = 0.05  # additive to cosine similarity for chunks tagging a named entity
CANDIDATE_POOL_MULTIPLIER = 3  # widen the candidate pool so boosted chunks can surface


class Retriever:
    """Embeds a query and searches the vector store for relevant chunks.

    When an EntityStore is provided, chunks tagged as mentioning an entity
    named in the query get a small score boost, applied over a wider
    candidate pool so a boosted chunk can surface even if its raw cosine
    similarity alone wouldn't have made the final top_k.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        ollama_client: OllamaClient,
        embedding_model: str,
        entity_store: EntityStore | None = None,
    ) -> None:
        self._vector_store = vector_store
        self._ollama_client = ollama_client
        self._embedding_model = embedding_model
        self._entity_store = entity_store

    def retrieve(self, query: str, top_k: int = 5) -> list[SearchResult]:
        query_embedding = self._ollama_client.embed(self._embedding_model, query)

        if self._entity_store is None:
            return self._vector_store.search(query_embedding, top_k=top_k)

        candidates = self._vector_store.search(
            query_embedding, top_k=top_k * CANDIDATE_POOL_MULTIPLIER
        )
        boosted = self._apply_entity_boost(query, candidates)
        return boosted[:top_k]

    def _apply_entity_boost(self, query: str, results: list[SearchResult]) -> list[SearchResult]:
        query_lower = query.lower()
        matched_entities = [e for e in self._entity_store.list_all() if e.name.lower() in query_lower]
        if not matched_entities:
            return results

        boosted_chunk_ids: set[str] = set()
        for entity in matched_entities:
            boosted_chunk_ids.update(m.chunk_id for m in self._entity_store.get_mentions(entity.id))

        for result in results:
            if result.chunk_id in boosted_chunk_ids:
                result.score += ENTITY_BOOST

        return sorted(results, key=lambda r: r.score, reverse=True)
