from __future__ import annotations

import json
import re
from dataclasses import dataclass

from src.database.entity_store import EntityMention, EntityStore
from src.pipeline.chunker import Chunk
from src.utils.logging import get_logger
from src.utils.ollama_client import OllamaClient, OllamaError

logger = get_logger(__name__)

BATCH_SIZE = 45  # chunks per LLM call - mechanism proven on M1E, widening to cut call count further

_ENTITY_TYPES = {"character", "location", "faction", "item"}

_SYSTEM_PROMPT = (
    "You identify named entities in Malifaux story text: characters, locations, "
    "factions, and items. Respond ONLY with a JSON array of objects, each with "
    '"name", "type" (one of character/location/faction/item), and "description" '
    "(a one-sentence description). If there are no named entities, respond with []. "
    "Do not include generic/unnamed references (e.g. \"the guard\", \"a soldier\")."
)

_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


@dataclass
class ExtractedEntity:
    name: str
    type: str
    description: str


def _batch_chunks(chunks: list[Chunk], batch_size: int = BATCH_SIZE) -> list[list[Chunk]]:
    return [chunks[i : i + batch_size] for i in range(0, len(chunks), batch_size)]


def _build_messages(batch_text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"Text:\n{batch_text}\n\nJSON array of entities:"},
    ]


def _parse_entities(response_text: str) -> list[ExtractedEntity]:
    """Parse the model's JSON-array response, tolerating extra prose around it."""
    match = _JSON_ARRAY_RE.search(response_text)
    if not match:
        return []
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError:
        logger.warning("Could not parse entity extraction response as JSON")
        return []

    entities = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        type_ = item.get("type")
        if not name or not type_:
            continue
        type_ = str(type_).strip().lower()
        if type_ not in _ENTITY_TYPES:
            continue
        entities.append(
            ExtractedEntity(
                name=str(name).strip(),
                type=type_,
                description=str(item.get("description", "")).strip(),
            )
        )
    return entities


def extract_entities_for_document(
    chunks: list[Chunk],
    document_id: str,
    ollama_client: OllamaClient,
    chat_model: str,
    entity_store: EntityStore,
) -> int:
    """Extract named entities from a document's chunks and index their mentions.

    Chunks are processed in batches (one LLM call per batch) rather than one call
    per chunk. Mention indexing then scans every chunk in the document for each
    entity found, not just the batch it was first mentioned in.

    Returns the number of distinct entities created.
    """
    if not chunks:
        return 0

    seen_names: dict[str, int] = {}  # lowercased name -> entity_id, dedupe within this doc
    batches = _batch_chunks(chunks)

    for i, batch in enumerate(batches):
        batch_text = "\n\n".join(c.text for c in batch)
        messages = _build_messages(batch_text)
        try:
            response = ollama_client.chat(chat_model, messages, temperature=0.2)
        except OllamaError as e:
            # One slow/failed batch shouldn't lose every entity found in the
            # other batches (and, critically, shouldn't skip mention indexing
            # for them - that still runs below over whatever was found).
            logger.warning(
                "Entity extraction batch %d/%d failed for %s, skipping: %s",
                i + 1, len(batches), document_id, e,
            )
            continue

        for extracted in _parse_entities(response):
            key = extracted.name.lower()
            if key in seen_names:
                continue
            entity_id = entity_store.add_entity(
                document_id, extracted.name, extracted.type, extracted.description
            )
            seen_names[key] = entity_id

    for name_lower, entity_id in seen_names.items():
        mentions = [
            EntityMention(
                entity_id=entity_id,
                chunk_id=chunk.chunk_id,
                document_id=document_id,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
            )
            for chunk in chunks
            if name_lower in chunk.text.lower()
        ]
        entity_store.add_mentions(mentions)

    logger.info("Extracted %d entities for %s", len(seen_names), document_id)
    return len(seen_names)
