# Session 4

**Branch:** `session-4` (not yet merged to `main`)
**OpenSpec changes:** `wiki-taxonomy-and-navigation` (archived `2026-07-08-wiki-taxonomy-and-navigation`), `entity-dedup-and-session-isolation` (archived `2026-07-08-entity-dedup-and-session-isolation`)

## What shipped

- **Fixed the broken wiki-to-chat link**: `base.html`'s top-nav "Chat" link was a relative `href="/"`, but the wiki is served by the backend (port 8000) while chat is a separate Gradio app (port 7860) - a genuinely different origin. `curl http://localhost:8000/` confirmed a 404. Fixed with a new `frontend.public_url` config value (defaults to `http://localhost:{frontend.port}`), passed into every wiki route's template context, so the link is now absolute.
- **Expanded the entity taxonomy** from 4 types (character/faction/item/location) to 7, adding `real-person` (game credits/authors), `creature` (undead/constructs/monsters), and `event`. `entity_extractor.py`'s live extraction prompt now uses all 7 for future uploads.
- **Threshold-gated dynamic tagging**: during reclassification, the model can propose a genuinely novel tag beyond the curated 7, but it only survives (becomes a real category) if at least 3 entities land in it - otherwise those entities revert to their prior type. Keeps the taxonomy from accumulating one-off noise.
- **One-off reclassification pass** (`scripts/reclassify_entities.py`) over the existing 133 entities, using each entity's stored name/description rather than re-reading source PDFs - a few minutes of small concurrent LLM calls instead of hours of re-extraction.
- **Per-type entity colors**: red/purple/gray/gold/teal per curated type instead of one bright red for every entity, with `real-person` deliberately muted/desaturated to read as meta content rather than story cast.
- **Wiki landing page**: `/wiki` now shows total entity count, document count, and a per-category breakdown above the category browsing, instead of directly being the category index. Dropped the old "first 5 entities per category" preview from the index - that content now lives only on category pages.

## Getting the reclassification prompt right took two real correction rounds

First run (discarded, DB restored from backup before persisting): the initial prompt ("real-person = a real-world person credited in the text") over-triggered on fictional characters who merely *had* an in-story occupation - "Jacob Samuels, the owner of Ringside", "Dr. Victor Ramos, president of the Miners and Steamfitters Union", "Michael Rutledge, a convicted mass murderer" all got mistyped as `real-person`. Fixed by rewriting the prompt to require *explicit book-credit language* ("Author of the M1E Core", "Writer", "Producer") and to explicitly say an in-story occupation does NOT make someone a real person.

Second run (also discarded, restored again): with the tightened prompt, actual fictional characters with descriptions were now correctly classified - but every entity with a **blank description** still got mistyped as `real-person`, 100% of the time. With no other signal, the model defaulted to "sounds like a plausible name -> real person" regardless of an explicit "if unsure, keep the current type" instruction in the prompt. Since this failure mode was completely consistent, the real fix was in code, not more prompt-wrangling: `reclassify_entities()` now skips the LLM call entirely for any entity with an empty/blank description and just keeps its original type - cheaper and more reliable than hoping the model restrains itself.

Third run (kept): exactly 10 real book credits moved to `real-person` (zero false positives - Nathan Caroland, Eric Johns, Kelly Brumley, and the rest of the M1E Core credits list), 4 legitimate non-human entities moved to `creature` (Sybelle, December, Takashi, Philip Tombers - a desiccated test-subject corpse), one location got correctly reclassified to faction, and all ambiguous/blank-description entities stayed exactly where they were. Spot-checked in the running wiki via Playwright.

## Other findings

- `data/MalifauxStories_TEST.pdf` is byte-identical to M1E (confirmed via `md5sum` - same checksum). Nothing new to ingest; both real documents (M1E, M2E) were already fully processed going into this session.

## Verification

120/120 tests passing (up from 108 at the end of session 3 - added reclassification unit/integration tests, config tests for `public_url`, entity-type/color regression tests). Backend + frontend restarted; live Playwright pass confirmed: the chat link is absolute and actually resolves (200, not 404), category tiles render in genuinely distinct colors, `real-person` is visibly muted relative to `character`, the landing page shows correct live stats (133 entities, 2 documents, per-category counts), and the reclassified data renders correctly in the running wiki (`real-person` category contains exactly the 10 credits and nothing else; `character` category still correctly contains Jacob Samuels/Dr. Victor Ramos/Michael Rutledge).

## Round 2: `entity-dedup-and-session-isolation`

After the taxonomy/navigation round shipped, the user asked to clear the remaining open items from prior sessions: the shared-conversation-ID bug, chat speed (further), and entity fragmentation. Two of the three carried a real trade-off or risk, so those were checked with the user before proceeding rather than decided unilaterally; the third (chunk boundaries in the multi-story anthologies) was explicitly deferred as too high-cost/uncertain for this round.

### Fixed: shared conversation ID

`src/frontend/app.py` had `conversation_id = gr.State(str(uuid.uuid4()))` - `gr.State`'s value is evaluated once at app-build time, not per session, so every browser session shared one conversation history. Gradio's own docs describe the fix: pass a callable and it's invoked fresh per session load. One-line change (`gr.State(lambda: str(uuid.uuid4()))`), verified live: two independent Playwright browser contexts submitting messages concurrently now show two distinct conversation IDs in the backend's query log (previously would have been identical).

### Investigated and rejected: a faster chat model

Pulled `llama3.2:1b` (vs. the current `llama3.2:latest`, 3B) and benchmarked both against the *actual* live retriever's real output for two real questions ("Who is Lady Justice?", "What is the Ortega family known for?") - not synthetic filler text, since an earlier synthetic-context test had produced a misleading hallucination ("Cadian Empire", a Warhammer 40K term, not Malifaux) that turned out to be an artifact of the test itself having no real grounding content. With real context, prompt evaluation was ~3x faster (6-7s vs 18-23s), but the 1B model hallucinated on both real questions anyway - confusing Perdita's siblings with monster types ("Sonnia (a Gremlin)", "Santiago (a Peacebringer)"). The 3B model stayed coherent and grounded on identical context both times. Speed isn't worth trading for fabricated lore in a RAG app whose core requirement is grounded answers - no model change ships; documented as a considered-and-rejected option rather than silently dropped.

### Entity deduplication - the approach had to be redesigned after the first attempt failed completely

First attempt: ask the model to cluster an entire type's entity list (e.g. all 97 characters) into duplicate groups in one call. Result: 10 proposed merge groups, **all of them wrong** - it merged three different real book-credit authors together ("Chrissy Monfette" absorbing "Eric Johns" and "Graeme Stevenson"), and merged unrelated locations ("Malifaux Station" absorbing "Malifaux" the city itself). It completely missed the actual known duplicates ("Molly Squidpiddge" variants, "Samael" variants) while inventing wrong ones. Discarded before persisting (dry-run only; DB was never touched).

Rewrote the approach: generate candidate pairs first via a cheap Python string-similarity pre-filter (exact-normalized-name match or substring match or a `difflib` ratio >= 0.7) within each type, then ask the model a narrow yes/no question about each *specific pair* rather than open-ended whole-list clustering, then union transitively-confirmed pairs (e.g. "McMourning" <-> "Douglas McMourning" <-> "Dr. Douglas McMourning" chains into one group) via a small union-find structure. This produced 9 merge groups on the real data, all of which checked out on inspection - exact-name duplicate rows (same name, extracted separately per document) merged with zero LLM calls needed (no ambiguity), plus the two originally-identified real fragmentation cases ("Molly Squidpiddge"/"Molly Squidpiddge (again)", and the 4-way "McMourning" chain). Notably, the model correctly declined to merge some superficially-similar candidates it wasn't confident about (e.g. two different "Samael"-named characters with inconsistent descriptions, "Sonnia"/"Sonnia Squidpiddge"/"Sonnia Criid") rather than forcing a merge - the conservative behavior the design was aiming for.

Applied via `scripts/dedupe_entities.py --dry-run` (reviewed) then for real, after backing up the database. 133 -> 122 entities (11 merged into 9 groups). Verified live in the wiki: only one "Molly Squidpiddge" entry remains, "Dr. Douglas McMourning" now carries 217 consolidated mentions (up from being split across 4 rows) with its fullest description intact, landing page stats correctly show 122.

## Verification

134/134 tests passing (up from 120 at the end of round 1 - added `merge_entities` tests, candidate-pair/union-find unit tests, pairwise-confirmation integration tests with fake Ollama clients covering transitive chains and failure handling). Backend + frontend restarted after each round; live Playwright/query-log verification confirmed both the session-isolation fix and the deduplicated wiki data.

## State at end of session

- `session-4` branch (not merged to `main` yet - stays isolated per this project's established session-branching convention until explicitly asked to merge).
- 134/134 tests, 7 capability specs (all synced), no active OpenSpec changes.
- Backend (port 8000) and frontend (port 7860) running with this session's build.
- The `../rauer-rebuild-session2-demo` worktree from session 3 still exists on disk (not removed), currently just a stale extra checkout of `main` - harmless but no longer serving any purpose now that `main`/`session-3` content has moved on.
- `llama3.2:1b` remains pulled locally (from the model investigation) but is not referenced by any config - harmless, just disk space, available for any future re-evaluation.

## Open items carried forward

- Chunking can straddle story boundaries in the M1E/M2E anthologies - explicitly deferred again this session (highest uncertainty/cost of the remaining items: needs re-extraction with font/heading metadata, re-chunking, and re-embedding, plus heuristic boundary-detection is inherently imperfect).
- Client-side wiki search (session 3) doesn't scale indefinitely - revisit if entity count grows an order of magnitude.
- The dynamic-tag threshold (3 entities, from the taxonomy round) and the dedup similarity threshold (0.7) are both untuned judgment calls, not derived from any real precision/recall measurement - fine at current scale, worth revisiting if either mechanism starts misbehaving as more documents are ingested.
