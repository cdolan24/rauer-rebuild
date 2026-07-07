from __future__ import annotations

from src.database.entity_store import Entity
from src.utils.ollama_client import OllamaClient

_SYSTEM_PROMPT = (
    "You write a short, engaging wiki-style summary paragraph (2-4 sentences) for a "
    "fictional entity from the Malifaux setting, based only on the given facts. Do not "
    "invent details beyond what's given."
)


def generate_entity_summary(
    entity: Entity, mention_count: int, ollama_client: OllamaClient, chat_model: str
) -> str:
    """Generate a wiki-style summary paragraph for an entity, grounded in its
    already-extracted description (not re-reading the source text)."""
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Name: {entity.name}\n"
                f"Type: {entity.type}\n"
                f"Known facts: {entity.description}\n"
                f"Mentioned in {mention_count} place(s) across the source material.\n\n"
                "Write the wiki summary paragraph:"
            ),
        },
    ]
    return ollama_client.chat(chat_model, messages, temperature=0.4)
