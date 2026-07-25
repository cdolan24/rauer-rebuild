from __future__ import annotations

from src.database.entity_store import Entity
from src.utils.ollama_client import OllamaClient

_SYSTEM_PROMPT = (
    "You write a detailed, engaging wiki-style article for a fictional entity from the "
    "Malifaux setting, grounded in the passages below (the entity's actual mentions in "
    "the source material) plus its known facts. Cover everything the passages reveal - "
    "personality, appearance, role, relationships, notable events - organized into "
    "multiple paragraphs where the material supports it. Do not invent details beyond "
    "what's given; if the passages are sparse, write a shorter article rather than "
    "padding it with invention."
)


def generate_entity_summary(
    entity: Entity,
    mention_count: int,
    mention_context: str,
    ollama_client: OllamaClient,
    chat_model: str,
) -> str:
    """Generate a wiki-style article for an entity, grounded in the actual
    text of its mentions (`mention_context`, e.g. from
    `pipeline.mention_context.gather_mention_context`) rather than only its
    one-sentence stored description."""
    passages = mention_context if mention_context.strip() else "(no passages available)"
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Name: {entity.name}\n"
                f"Type: {entity.type}\n"
                f"Known facts: {entity.description}\n"
                f"Mentioned in {mention_count} place(s) across the source material.\n\n"
                f"Passages mentioning {entity.name}:\n{passages}\n\n"
                "Write the wiki article:"
            ),
        },
    ]
    return ollama_client.chat(chat_model, messages, temperature=0.4)
