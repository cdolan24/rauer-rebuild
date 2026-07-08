## Why

Two known limitations, both previously documented as open items, get addressed here: every browser session shared one conversation history (a `gr.State` default that was only ever computed once at app-build time, not per session - confirmed via a live two-session test showing identical conversation IDs), and the wiki's entity list has real fragmentation - the same underlying entity appears as multiple separate rows under different name variants (e.g. "Molly Squidpiddge", "Molly Squidpiddge (again)", and "Molly-girl" as three distinct entities; "Samael", "Samael Hopkins", and "Deputy Samael Hopkins" similarly split). A faster/smaller chat model was also investigated as a separate speed lever - rejected after direct evidence of hallucination on real retrieval context (see design.md), so no change ships from that investigation.

## What Changes

- Fix `conversation_id`'s `gr.State` default to be a callable (Gradio invokes callables fresh per session load) instead of a value computed once at app-build time.
- Add an LLM-assisted entity deduplication pass: for each entity type, ask the model to identify name-variant duplicates from stored name/description alone (no source re-reading), merge mentions onto a single surviving entity, and remove the duplicates. Run once against the current entity set via a new one-off script, with a `--dry-run` mode to review proposed merges before applying them.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `chat-frontend`: add a requirement that each browser session gets an independent conversation history.
- `entity-extraction`: add a requirement for duplicate entity merging.

## Impact

- `src/frontend/app.py` (conversation_id fix - one line).
- `src/database/entity_store.py` (new `merge_entities` method).
- `src/pipeline/entity_deduper.py` (new module: LLM-assisted duplicate-group detection).
- `scripts/dedupe_entities.py` (new one-off CLI, parallel to `scripts/reclassify_entities.py`).
