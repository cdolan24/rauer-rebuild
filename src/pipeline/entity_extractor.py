from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from src.database.entity_store import Entity, EntityMention, EntityStore
from src.pipeline.chunker import Chunk
from src.utils.logging import get_logger
from src.utils.ollama_client import OllamaClient, OllamaError

logger = get_logger(__name__)

BATCH_SIZE = 20  # chunks per LLM call - 45 caused 9/54 batches to time out even at
# MAX_WORKERS=3 and a 300s timeout on the real M1E document, since a 45-chunk
# batch is slow enough on its own (CPU-only inference) that queueing behind
# even one other request could exceed the timeout before the model started.
# A smaller batch is faster per-call, bounding worst-case queued wait time,
# at the cost of more total batches/calls.
# Chat-model calls (unlike embeddings) are slow enough, and Ollama's default
# config only actually runs one model inference at a time regardless of how
# many requests are in flight, that a wide worker count just queues requests
# up behind each other - and each queued request's client-side timeout clock
# is already running while it waits its turn. On a real 629-page document (54
# batches), 8-way concurrency caused every single batch to time out. Keeping
# this low bounds the worst-case queueing depth a request can be stuck behind.
MAX_WORKERS = 3

# Single source of truth for the curated taxonomy - also imported by the
# one-off reclassification script so both stay in sync.
CURATED_ENTITY_TYPES = {
    "character",
    "location",
    "faction",
    "item",
    "real-person",
    "creature",
    "event",
}

_SYSTEM_PROMPT = (
    "You identify named entities in Malifaux story text: characters, locations, "
    "factions, items, real people, creatures, and events. Respond ONLY with a JSON "
    'array of objects, each with "name", "type" (one of character/location/faction/'
    'item/real-person/creature/event), and "description" (a one-sentence description). '
    "Use real-person for real-world people credited in the text (e.g. authors, artists, "
    "producers), not fictional characters. Use creature for non-human cast (undead, "
    "constructs, monsters) rather than character. Use event for significant in-world "
    "occurrences referenced in the text, rather than describing them under another "
    "entity. If there are no named entities, respond with []. Do not include "
    'generic/unnamed references (e.g. "the guard", "a soldier").'
)

_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)

# A novel (non-curated) tag proposed during reclassification must cover at
# least this many entities to survive as a real category - otherwise those
# entities keep their prior type. Keeps the taxonomy from accumulating
# one-off noise tags.
DYNAMIC_TAG_MIN_COUNT = 3

_RECLASSIFY_SYSTEM_PROMPT = (
    "You categorize a named entity from a Malifaux story/game document, given its "
    "current type, name, and description. Respond ONLY with a JSON object: "
    '{"type": "<type>"}. Prefer one of these curated types: character, faction, '
    "item, location, real-person, creature, event.\n\n"
    "Use real-person ONLY when the description explicitly credits someone for "
    "producing the book/document itself - e.g. \"Author of the M1E Core\", "
    "\"Writer\", \"Producer\", \"Artist for the M1E Core\", \"graphic designer\", "
    "someone named in a credits/staff list. A character who merely HAS an "
    "in-story job (a shop owner, a union president, a boxer, a portrait painter "
    "hired by another character) is NOT a real-person - they are a character "
    "within the fiction, even though their description mentions an occupation.\n\n"
    "Use creature for non-human cast: undead, constructs, monsters, spirits.\n"
    "Use event for a significant in-world occurrence, not a person or place.\n\n"
    "If the description is empty, vague, or you are not confident a change is "
    "warranted, respond with the entity's CURRENT type unchanged rather than "
    "guessing. Only propose a novel type beyond this curated list rarely, and "
    "only when the entity clearly doesn't belong in any of them."
)

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_TAG_RE = re.compile(r"[a-z][a-z0-9-]*")


@dataclass
class ExtractedEntity:
    name: str
    type: str
    description: str


@dataclass
class ExtractionResult:
    entity_count: int
    uncovered_chunk_ids: list[str]


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
        if type_ not in CURATED_ENTITY_TYPES:
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
    max_workers: int = MAX_WORKERS,
) -> ExtractionResult:
    """Extract named entities from a document's chunks and index their mentions.

    Chunks are processed in batches (one LLM call per batch) rather than one call
    per chunk, and batches are sent concurrently (same rationale as
    pipeline/embeddings.py: the LLM round-trip, not local work, is the
    bottleneck). Mention indexing then scans every chunk in the document for
    each entity found, not just the batch it was first mentioned in.

    A batch that fails is retried once before being given up on - a single
    timeout under concurrent load doesn't mean the same batch would fail
    again once its turn comes, and a batch that fails twice loses coverage
    entirely (no entities from it, ever), so it's worth one retry.

    Returns an ExtractionResult with the number of distinct entities created
    and the chunk ids belonging to any batch that still failed after retry.
    """
    if not chunks:
        return ExtractionResult(entity_count=0, uncovered_chunk_ids=[])

    batches = _batch_chunks(chunks)

    def _call_batch(indexed_batch: tuple[int, list[Chunk]]) -> str | None:
        i, batch = indexed_batch
        batch_text = "\n\n".join(c.text for c in batch)
        messages = _build_messages(batch_text)
        last_error: OllamaError | None = None
        for _ in range(2):
            try:
                return ollama_client.chat(chat_model, messages, temperature=0.2)
            except OllamaError as e:
                last_error = e
        # One slow/failed batch shouldn't lose every entity found in the
        # other batches (and, critically, shouldn't skip mention indexing
        # for them - that still runs below over whatever was found).
        logger.warning(
            "Entity extraction batch %d/%d failed for %s after retry, skipping: %s",
            i + 1, len(batches), document_id, last_error,
        )
        return None

    with ThreadPoolExecutor(max_workers=min(max_workers, len(batches))) as executor:
        responses = list(executor.map(_call_batch, enumerate(batches)))

    uncovered_chunk_ids = [
        chunk.chunk_id
        for response, batch in zip(responses, batches)
        if response is None
        for chunk in batch
    ]

    # Entity creation happens single-threaded after all responses are in, so
    # there's no concurrent-write contention on entity_store or the dedupe dict.
    seen_names: dict[str, int] = {}  # lowercased name -> entity_id, dedupe within this doc
    for response in responses:
        if response is None:
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

    logger.info(
        "Extracted %d entities for %s (%d/%d chunks uncovered)",
        len(seen_names), document_id, len(uncovered_chunk_ids), len(chunks),
    )
    return ExtractionResult(entity_count=len(seen_names), uncovered_chunk_ids=uncovered_chunk_ids)


def _build_reclassify_messages(entity: Entity) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": _RECLASSIFY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Name: {entity.name}\nCurrent type: {entity.type}\n"
                f"Description: {entity.description}\n\nJSON:"
            ),
        },
    ]


def _parse_reclassification(response_text: str) -> str | None:
    """Parse the model's `{"type": "..."}` response into a normalized tag,
    tolerating extra prose. Returns None if nothing usable was found."""
    match = _JSON_OBJECT_RE.search(response_text)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    type_ = obj.get("type")
    if not type_ or not isinstance(type_, str):
        return None
    type_ = type_.strip().lower()
    return type_ if _TAG_RE.fullmatch(type_) else None


def reclassify_entities(
    entities: list[Entity],
    ollama_client: OllamaClient,
    chat_model: str,
    max_workers: int = MAX_WORKERS,
) -> dict[int, str]:
    """Re-type existing entities against the current taxonomy from their
    stored name/description, without re-reading source documents.

    The model may propose a novel tag beyond the curated set, but a novel
    tag only survives if at least DYNAMIC_TAG_MIN_COUNT entities land in it;
    otherwise those entities keep their original type.

    Returns a mapping of entity_id -> new type, only for entities whose type
    actually changed. Callers persist this via EntityStore.set_type.
    """
    if not entities:
        return {}

    def _classify(entity: Entity) -> tuple[int, str, str]:
        if not entity.description.strip():
            # With no description, there's no real signal to classify from -
            # empirically, the model defaults to "sounds like a real name"
            # and mistypes every blank-description entity as real-person.
            # Cheaper and more accurate to just leave these alone.
            return entity.id, entity.type, entity.type
        messages = _build_reclassify_messages(entity)
        try:
            response = ollama_client.chat(chat_model, messages, temperature=0.0)
        except OllamaError as e:
            logger.warning(
                "Reclassification failed for entity %d (%s), keeping type '%s': %s",
                entity.id, entity.name, entity.type, e,
            )
            return entity.id, entity.type, entity.type
        parsed = _parse_reclassification(response)
        new_type = parsed if parsed else entity.type
        return entity.id, entity.type, new_type

    with ThreadPoolExecutor(max_workers=min(max_workers, len(entities))) as executor:
        results = list(executor.map(_classify, entities))

    novel_tag_counts: dict[str, int] = {}
    for _, _, new_type in results:
        if new_type not in CURATED_ENTITY_TYPES:
            novel_tag_counts[new_type] = novel_tag_counts.get(new_type, 0) + 1

    updates: dict[int, str] = {}
    for entity_id, original_type, new_type in results:
        if new_type not in CURATED_ENTITY_TYPES and novel_tag_counts[new_type] < DYNAMIC_TAG_MIN_COUNT:
            final_type = original_type
        else:
            final_type = new_type
        if final_type != original_type:
            updates[entity_id] = final_type

    return updates
