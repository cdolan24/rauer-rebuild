## Why

The wiki works end-to-end but is thin: each entity page is roughly a paragraph, factions and locations get no special treatment despite being natural browsing hubs (guild rosters, a map-style location index), there is no way to see how entities relate to one another, and some entities that should have been wikified are missing entirely. The user wants the wiki to be worth spending time in, not just a byproduct of RAG ingestion.

## What Changes

- Regenerate entity summaries to be substantially longer/denser - pull in everything known about the entity (all mention contexts across all its chunks, not a sampled subset) rather than a single-paragraph blurb.
- Add dedicated hub/index pages for two entity types:
  - A faction ("guild") page lists all member characters, not just its own description.
  - A locations page acts as a map-style index of all locations, each linking to its own entity page.
- Add entity relationships:
  - A new relationship-extraction pipeline stage (LLM pass over each entity's mention context) identifies related entities and the nature of the relationship (e.g. "member of", "rival of", "located in").
  - Each entity's wiki page gets a "Relationships" section listing these.
  - A separate wiki-wide relationship graph page visualizes all extracted relationships.
- Audit entity coverage before deciding a fix: compare current extracted entity counts/types against the source PDFs (M1E, M2E) to determine whether missing entities are an extraction-recall/prompt problem (entity_extractor.py's taxonomy or system prompt under-extracting certain categories) or a coverage gap (some ingested content never actually gets scanned for entities). Fix whichever the audit finds, scoped to what's actually broken.

## Capabilities

### New Capabilities
- `entity-relationships`: LLM-derived relationships between entities (extraction, storage, and retrieval), independent of how the wiki renders them.

### Modified Capabilities
- `wiki`: entity pages show substantially fuller summaries and a relationships section; new faction and location hub/index pages; new relationship graph page.
- `entity-extraction`: extraction coverage is audited and, depending on findings, either the extraction prompt/taxonomy or the ingestion coverage path is fixed so entities that should be captured are not silently missed.

## Impact

- `src/wiki/summary.py` (`generate_entity_summary`): change how much mention context is gathered and summarized per entity.
- `src/wiki/templates/`: new faction/location hub templates, relationships section on entity pages, new graph page/template.
- `src/wiki/routes` (or equivalent Flask/FastAPI routing module serving wiki pages): new routes for faction hub, location hub, and relationship graph.
- `src/pipeline/entity_extractor.py`, `src/pipeline/entity_deduper.py`: possible prompt/taxonomy/coverage fix depending on audit outcome.
- `src/database/entity_store.py`: new schema/table for relationships (entity_id, related_entity_id, relationship description), new query methods.
- New `src/pipeline/relationship_extractor.py` (or similarly-named module) alongside the existing entity-extraction pipeline stage, following the existing low-concurrency (`MAX_WORKERS`-style) pattern for LLM calls against local Ollama.
- `scripts/` may need a one-off/backfill script analogous to `scripts/extract_entities.py`, to run relationship extraction (and, if needed, entity re-extraction) against already-ingested documents (M1E, M2E) without a full reprocess.
