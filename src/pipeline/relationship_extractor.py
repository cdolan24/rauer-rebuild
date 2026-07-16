from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor

from src.database.entity_store import Entity, EntityStore
from src.database.vector_store import VectorStore
from src.pipeline.mention_context import gather_mention_context
from src.utils.logging import get_logger
from src.utils.ollama_client import OllamaClient, OllamaError

logger = get_logger(__name__)

# See entity_extractor.py's MAX_WORKERS comment: wide concurrency just queues
# chat-model calls behind each other once Ollama is serializing inference
# anyway, and each queued request's timeout clock runs the whole time it waits.
MAX_WORKERS = 3

# Caps how many candidates go into a single prompt (after the context-name
# pre-filter below) - a real-world run against ~380 stored entities showed
# unfiltered candidate lists blow up prompt size enough to raise the timeout
# rate to ~26%, far above entity_extractor.py's ~1%. Keeps the worst case
# bounded even if many candidate names happen to appear in one entity's
# passages.
MAX_CANDIDATES = 40

_SYSTEM_PROMPT = (
    "You identify relationships between a given fictional entity from the Malifaux "
    'setting and other already-known entities, based on the passages describing the '
    "given entity. Respond ONLY with a JSON array of objects, each with \"name\" (the "
    "related entity's name, copied exactly from the candidate list) and \"description\" "
    '(a short phrase describing the relationship, e.g. "member of", "rival of", '
    '"located in", "ally of"). Only include a candidate if the passages actually '
    "indicate a relationship to it - do not guess. If there are no clear relationships, "
    "respond with []."
)

_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


def _build_messages(entity: Entity, mention_context: str, candidates: list[Entity]) -> list[dict[str, str]]:
    candidate_list = "\n".join(f"- {c.name} ({c.type})" for c in candidates)
    passages = mention_context if mention_context.strip() else "(no passages available)"
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Entity: {entity.name} ({entity.type})\n"
                f"Passages mentioning {entity.name}:\n{passages}\n\n"
                f"Candidate entities it might relate to:\n{candidate_list}\n\n"
                "JSON array of relationships:"
            ),
        },
    ]


def _filter_candidates_by_context(candidates: list[Entity], mention_context: str) -> list[Entity]:
    """Only ask about candidates whose name actually appears in the mention
    context - if a candidate's name never appears in the passages describing
    the entity, the model has no textual basis to relate them anyway. Same
    cheap-prefilter-before-LLM-call pattern as entity_deduper.py's candidate
    pairs, and keeps prompt size from scaling with the whole entity store."""
    context_lower = mention_context.lower()
    matched = [c for c in candidates if c.name.lower() in context_lower]
    return matched[:MAX_CANDIDATES]


def _parse_relationships(response_text: str) -> list[tuple[str, str]]:
    """Parse the model's JSON-array response, tolerating extra prose."""
    match = _JSON_ARRAY_RE.search(response_text)
    if not match:
        return []
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError:
        logger.warning("Could not parse relationship extraction response as JSON")
        return []

    results = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        description = item.get("description")
        if not name or not description:
            continue
        results.append((str(name).strip(), str(description).strip()))
    return results


def extract_relationships_for_entity(
    entity: Entity,
    mention_context: str,
    candidates: list[Entity],
    ollama_client: OllamaClient,
    chat_model: str,
) -> list[tuple[int, str]]:
    """Ask the LLM which of `candidates` the given entity relates to, and how,
    grounded in `mention_context` (see pipeline.mention_context). Matches the
    model's response back to candidate entities by name (case-insensitive)
    rather than trusting it to invent ids.

    Returns a list of (related_entity_id, description). Never raises
    OllamaError - a failure here just means no relationships found this pass.
    """
    if not candidates or not mention_context.strip():
        return []

    messages = _build_messages(entity, mention_context, candidates)
    try:
        response = ollama_client.chat(chat_model, messages, temperature=0.2)
    except OllamaError as e:
        logger.warning(
            "Relationship extraction failed for entity %d (%s), skipping: %s",
            entity.id, entity.name, e,
        )
        return []

    by_name = {c.name.lower(): c.id for c in candidates}
    results = []
    for name, description in _parse_relationships(response):
        related_id = by_name.get(name.lower())
        if related_id is None or related_id == entity.id:
            continue
        results.append((related_id, description))
    return results


def extract_relationships_for_document(
    entities: list[Entity],
    entity_store: EntityStore,
    vector_store: VectorStore,
    ollama_client: OllamaClient,
    chat_model: str,
    max_workers: int = MAX_WORKERS,
) -> int:
    """Extract and store relationships for a set of entities (typically a
    document's entities, though candidates are drawn from the whole store so
    a relationship can span documents, e.g. the same location referenced in
    both M1E and M2E). Candidates are filtered down to those actually named
    in the entity's own mention context before being sent to the LLM (see
    _filter_candidates_by_context) - otherwise prompt size scales with the
    whole entity store, which is what caused this stage's timeout rate to
    balloon on a real ~380-entity backfill.

    Runs one LLM call per entity, concurrently at low worker count (same
    rationale as entity_extractor.py). A single entity's failure doesn't
    affect the others - each call already catches its own OllamaError.

    Returns the number of relationships stored.
    """
    if not entities:
        return 0

    all_entities = entity_store.list_all()

    def _process(entity: Entity) -> list[tuple[int, int, str]]:
        mentions = entity_store.get_mentions(entity.id)
        mention_context = gather_mention_context(mentions, vector_store)
        candidates = [e for e in all_entities if e.id != entity.id]
        candidates = _filter_candidates_by_context(candidates, mention_context)
        found = extract_relationships_for_entity(
            entity, mention_context, candidates, ollama_client, chat_model
        )
        return [(entity.id, related_id, description) for related_id, description in found]

    with ThreadPoolExecutor(max_workers=min(max_workers, len(entities))) as executor:
        results = list(executor.map(_process, entities))

    stored = 0
    for relationships in results:
        for entity_id, related_id, description in relationships:
            entity_store.add_relationship(entity_id, related_id, description)
            stored += 1

    logger.info("Extracted %d relationship(s) across %d entities", stored, len(entities))
    return stored
