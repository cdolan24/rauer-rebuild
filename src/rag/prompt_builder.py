from __future__ import annotations

from src.database.vector_store import SearchResult
from src.rag.conversation_store import ConversationTurn

SYSTEM_PROMPT = (
    "You are a knowledgeable guide to the Malifaux story/lore documents provided as context. "
    "Answer as if the reader has no prior knowledge of the material: explain who or what things "
    "are, provide relevant background, and note connections to related concepts. "
    "Base your answer only on the provided context. If the context doesn't fully answer the "
    "question, say what you can and note the gap rather than inventing details."
)


def _format_context(chunks: list[SearchResult]) -> str:
    blocks = []
    for chunk in chunks:
        if chunk.page_start == chunk.page_end:
            pages = f"p. {chunk.page_start}"
        else:
            pages = f"pp. {chunk.page_start}-{chunk.page_end}"
        blocks.append(f"[Source: {chunk.document_id}, {pages}]\n{chunk.text}")
    return "\n\n".join(blocks)


def build_messages(
    question: str,
    chunks: list[SearchResult],
    history: list[ConversationTurn],
) -> list[dict[str, str]]:
    """Build a chat message list for the local LLM: system prompt, prior turns, then the
    current question with its retrieved context."""
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    for turn in history:
        messages.append({"role": "user", "content": turn.question})
        messages.append({"role": "assistant", "content": turn.answer})

    context = _format_context(chunks)
    messages.append(
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {question}",
        }
    )
    return messages
