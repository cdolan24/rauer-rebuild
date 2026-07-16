## Context

Today `generate_entity_summary` (`src/wiki/summary.py`) only ever sees the entity's one-sentence `description` (captured once, at extraction time) plus a bare mention count - it never looks at the actual mention text. That's the direct cause of "only a paragraph": there's almost nothing to summarize from. Getting a denser summary means pulling real context (the chunk text at each mention) into the prompt, not just asking the model to try harder with the same thin input.

The wiki (`src/wiki/routes.py` + `src/wiki/templates/`) currently has three page types: index (category browsing), category (flat entity list), and entity (summary + infobox + citations). There is no notion of "this faction's members" or "all locations as a set" - `wiki_category` just lists every entity of a type with no additional structure, and there is nothing that connects two entities to each other at all. Entities and mentions are stored in SQLite (`src/database/entity_store.py`); relationships are new ground - no schema exists for them.

Entity extraction (`src/pipeline/entity_extractor.py`) runs one LLM call per batch of chunks with a fixed prompt/taxonomy (character, location, faction, item, real-person, creature, event) and only accepts entities matching that taxonomy (see `CURATED_ENTITY_TYPES`, `_parse_entities`). Missing entities could come from: the prompt/taxonomy itself being too narrow or under-eliciting certain kinds of names, chunks that never get scanned at all (coverage), the parser silently dropping malformed model output, or genuinely low-signal mentions (e.g. named once in passing) that a reasonable extractor would still skip. This design does not assume which; the audit (see Decisions) determines the fix.

All local LLM calls go through `OllamaClient` against Ollama, which serializes inference on this dev machine - every existing concurrent LLM-calling stage (`entity_extractor.py`, `entity_deduper.py`, `image_extractor.py`) uses a low `MAX_WORKERS` (2-3) for exactly this reason (see session 6 log). Any new LLM-calling stage here (richer summaries, relationship extraction) must follow the same pattern or it will reproduce the same timeout failures already seen and fixed once this session.

## Goals / Non-Goals

**Goals:**
- Entity summaries are grounded in real mention context, not just a one-line description, and are noticeably longer/denser as a result.
- Factions and locations get dedicated hub pages that aggregate their members/instances.
- Relationships between entities are extracted once (LLM pass, low concurrency, following the existing pattern), stored, and surfaced both per-entity and as a wiki-wide graph.
- The audit determines, with evidence from the actual DB and source PDFs, whether missing entities are a recall/prompt problem or a coverage problem, and the chosen fix targets that specific cause.
- All new LLM-calling pipeline stages are safe to re-run against already-ingested documents (M1E, M2E) without a full document reprocess, consistent with the existing `scripts/extract_entities.py` / `scripts/dedupe_entities.py` pattern.

**Non-Goals:**
- No change to the core entity taxonomy (character/location/faction/item/real-person/creature/event) unless the audit specifically finds the taxonomy itself is the cause of missing entities.
- No interactive graph editing (add/remove/correct relationships by hand) - the graph view is read-only.
- No client-side graph library evaluation beyond what's needed for a basic node-link view; this is not meant to become a full graph-analysis tool.
- Not re-litigating the vision-model pipeline (session 6) or the M2E reprocess - this change is scoped to wiki depth/relationships/coverage only, and is expected to land before M2E is reprocessed.

## Decisions

### Richer summaries: feed real mention context, not just the stored description
`generate_entity_summary` will be changed to accept the entity's actual mention text (chunk contents at each mention, deduplicated/truncated to a reasonable token budget) instead of only `entity.description`. The caller (`ingest.py`'s summarization step and `wiki/routes.py`'s on-demand fallback) already has access to `EntityMention` records and can fetch chunk text via `VectorStore.get_chunks_by_document` (index once by `chunk_id` per document, since mentions are already scoped to one document per entity... note an entity can have mentions across multiple documents if deduped across documents, so this needs to group mentions by `document_id` and fetch each document's chunks once, not per-mention).
- Alternative considered: increase `num_predict`/prompt-engineer the existing thin prompt to "be more detailed" - rejected, because the model has no more real information in the current prompt regardless of instruction; asking it to elaborate on one sentence just produces padding/invention, which conflicts with the existing "Do not invent details beyond what's given" instruction.
- Trade-off: larger prompts per entity = slower summary generation and higher risk of the same queueing/timeout issue entity extraction hit. Mitigate by capping how much mention text is included (e.g. first N mentions or a character budget) rather than concatenating unbounded text for entities with hundreds of mentions.

### Faction and location hub pages: new routes + templates, no new storage
A faction's members are exactly the characters (and other entity types, if relevant) that co-occur in mentions with that faction, OR - simpler and more consistent with existing data - members are determined by the new relationship-extraction stage (a "member of" relationship pointing at the faction). This makes the hub page a read view over the relationships table rather than a separate ad hoc "membership" concept, so there's one source of truth for entity-to-entity structure instead of two.
- `wiki/routes.py` gains `/wiki/faction/{entity_id}` and `/wiki/locations` (or similar) routes; new templates `faction.html`, `locations.html` extending `base.html` the same way `category.html` does.
- Locations hub is a single index page (not per-location) listing every `location`-typed entity, since "map-style index" implies one browsable set, not a hub per location; individual location detail stays on the existing entity page (now with its own relationships).

### Relationships: new pipeline stage + storage, LLM-derived from mention context
New `src/pipeline/relationship_extractor.py`, structurally parallel to `entity_deduper.py`: given an entity and its mention context (same chunk text gathered for summaries - reuse, don't refetch), ask the LLM to identify related entities (by name, matched back to existing `Entity` rows the same way mention indexing does case-insensitive name matching) and a short free-text relationship description. Runs after entity extraction + dedup (needs the deduped entity set to reference stable names) and after summaries (can reuse the same gathered mention context) as a new ingestion step, with its own low `MAX_WORKERS`.
- Storage: new `entity_relationships` table in `entity_store.py` - `(id, entity_id, related_entity_id, description)`. Store both directions is unnecessary if the graph/relationship queries are written to look up relationships where the entity is on either side (simpler write, one row per detected relationship pair) - a query helper (`get_relationships(entity_id)`) checks both `entity_id` and `related_entity_id` columns.
- Alternative considered: a typed relationship (`member_of`, `rival_of`, ...) enum, mirroring the entity-type taxonomy. Rejected for v1: relationships in narrative text are far more varied and harder to force into a fixed taxonomy than entity types were; free-text description (as the user asked for: "member of Guild", "rival of X") is simpler and avoids a second dynamic-tagging mechanism. Can be revisited later if the wiki needs to filter/color relationships by type.
- Graph page: a single `/wiki/graph` route rendering all entities as nodes and relationships as edges. Given the existing frontend has no JS graph library, use a minimal client-side approach (e.g. a small vanilla-JS force-layout or an existing lightweight library loaded via CDN, consistent with how the rest of the wiki frontend is built - check `base.html`/existing templates for current JS dependency conventions before choosing). This is the one piece of real UI-lift the user flagged as acceptable to be bigger.

### Coverage audit before any extraction fix
Before touching `entity_extractor.py`'s prompt or taxonomy, run an audit pass: for M1E and M2E, compare (a) the count/list of currently-extracted entities against (b) a manual/spot-check read of a sample of source pages, and (c) confirm every chunk in each document was actually included in some extraction batch (cross-check chunk counts against batches processed, since the session 6 timeout bug is known to have caused *silent* batch failures - `_call_batch` logs a warning and returns `None` on `OllamaError`, and mention indexing for chunks in a failed batch never runs at all for entities that would have been found only in that batch). This last point is a strong candidate: a coverage gap from failed batches, not a prompt-recall problem, given the entity-extraction regression already found and being fixed in parallel (97 -> 6 entities on M1E was caused by exactly this).
- Only after the audit confirms (or rules out) each candidate cause does the actual fix get scoped in tasks.md - this design deliberately does not pre-commit to "widen the prompt" vs. "improve batch reliability" vs. "add a retry for failed batches".

## Risks / Trade-offs

- [Risk] Richer summaries and relationship extraction both add real LLM-call volume to ingestion, on top of entity extraction that already regressed once under concurrency. → Mitigation: reuse gathered mention context between summary and relationship generation (one context-gathering pass, two LLM calls), keep both stages at the same low `MAX_WORKERS`/raised-timeout pattern already fixed for entity extraction, and make both backfillable via standalone scripts (like `extract_entities.py`) so a full document reprocess is never required to pick up fixes.
- [Risk] Relationship extraction quality depends entirely on mention-context quality - an entity with few/short mentions will get few/weak relationships, same limitation as summaries. → Mitigation: none needed beyond documenting it; this is an inherent data limitation, not a bug.
- [Risk] Free-text relationship descriptions can't be filtered/grouped as cleanly as typed entities. → Mitigation: accepted trade-off (see Decisions); revisit if the graph view turns out to need type-based styling.
- [Risk] Backfilling relationships/summaries for M1E/M2E without a full reprocess requires new one-off scripts (analogous to existing ones) - if those don't already generalize cleanly, this is more work than it looks. → Mitigation: model the new scripts directly on `scripts/extract_entities.py`'s existing shape (load config, load already-ingested chunks/entities, run the pipeline function, done).

## Open Questions

- Should relationship extraction see ALL of an entity's mentions, or the same capped/truncated context as summaries? (Leaning: same capped context, reusing the fetch - see Decisions.)
- Exact client-side approach for the graph page (vanilla JS vs. a small CDN-loaded library) - defer to whatever `tasks.md` implementation finds is consistent with the current frontend's JS conventions once that's inspected directly.
