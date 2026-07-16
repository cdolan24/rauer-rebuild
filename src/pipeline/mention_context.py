from __future__ import annotations

from src.database.entity_store import EntityMention
from src.database.vector_store import VectorStore

# Caps how much mention text feeds a single LLM prompt (summary or
# relationship generation) - an entity mentioned hundreds of times would
# otherwise blow up prompt size/latency for diminishing returns.
MAX_MENTIONS = 25
MAX_CHARS = 6000


def gather_mention_context(
    mentions: list[EntityMention],
    vector_store: VectorStore,
    max_mentions: int = MAX_MENTIONS,
    max_chars: int = MAX_CHARS,
) -> str:
    """Fetch the chunk text for an entity's mentions, grounding a summary or
    relationship-extraction prompt in what the source text actually says
    rather than just the entity's one-sentence stored description.

    Chunks are fetched once per document (via VectorStore.get_chunks_by_document),
    not once per mention, since an entity can be mentioned many times in the
    same document. Capped by max_mentions/max_chars so an entity with a huge
    mention count doesn't blow up prompt size.
    """
    if not mentions:
        return ""

    by_document: dict[str, list[EntityMention]] = {}
    for mention in mentions:
        by_document.setdefault(mention.document_id, []).append(mention)

    texts: list[str] = []
    total_chars = 0
    mentions_used = 0
    for document_id, doc_mentions in by_document.items():
        if mentions_used >= max_mentions or total_chars >= max_chars:
            break
        chunk_text_by_id = {
            chunk.chunk_id: chunk.text for chunk in vector_store.get_chunks_by_document(document_id)
        }
        for mention in doc_mentions:
            if mentions_used >= max_mentions or total_chars >= max_chars:
                break
            text = chunk_text_by_id.get(mention.chunk_id)
            if not text:
                continue
            texts.append(text)
            total_chars += len(text)
            mentions_used += 1

    return "\n\n".join(texts)
