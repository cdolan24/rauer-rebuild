from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from src.pipeline.chunker import Chunk
from src.utils.ollama_client import OllamaClient, OllamaError


class EmbeddingError(Exception):
    """Raised when embeddings cannot be generated for one or more chunks."""


@dataclass
class EmbeddedChunk:
    chunk: Chunk
    embedding: list[float]


def embed_chunks(
    chunks: list[Chunk],
    client: OllamaClient,
    model: str,
    max_workers: int = 8,
) -> list[EmbeddedChunk]:
    """Generate an embedding for each chunk via the local Ollama embedding model.

    Requests are issued concurrently (Ollama serves them without needing a
    response back before sending the next), which matters for large PDFs
    where sequential per-chunk HTTP round-trips would otherwise dominate
    ingestion time. Output order matches input chunk order.

    Raises:
        EmbeddingError: if the embedding service is unreachable or fails for any chunk.
    """
    if not chunks:
        return []

    def _embed_one(chunk: Chunk) -> list[float]:
        try:
            return client.embed(model, chunk.text)
        except OllamaError as e:
            raise EmbeddingError(f"Failed to embed chunk '{chunk.chunk_id}': {e}") from e

    with ThreadPoolExecutor(max_workers=min(max_workers, len(chunks))) as executor:
        vectors = list(executor.map(_embed_one, chunks))

    return [EmbeddedChunk(chunk=c, embedding=v) for c, v in zip(chunks, vectors)]
