## 1. Coverage audit (do first - determines scope of section 2)

- [x] 1.1 For M1E and M2E, cross-check `entity_extractor.py`'s per-batch success/failure against total chunk count to identify any chunks never covered by a successful batch (use existing logging/timeout data from the recent M1E regression as a starting point). Finding: confirmed via code review that a failed batch's response is `None` and is skipped entirely with no retry and no backfill - every chunk in that batch contributes zero entities and (since entity names are never even seen) zero mentions. This is a definite, mechanical coverage-gap cause, matching M1E's 97->6 regression (9/54 batches failed under the old code).
- [x] 1.2 Spot-check a sample of source pages from M1E/M2E against currently-extracted entities to look for names that should have been caught but weren't, independent of the batch-failure question. After the fixed-pipeline M1E backfill completed (360 entities, up from 6 regressed / 97 original), sampled pages 100, 250, and 400 of the processed text against the extracted set: Ortega family (all variants), Hoffman, Lady Justice, The Watcher, Mattheson/Lucius, Bellaventine Thorpe, and Guild variants were all present. Only "Stalker 263" (page 400) was missed - consistent with that page likely falling in one of the batches affected by the one network timeout or the ~16 batches whose LLM response didn't parse as valid JSON (both logged during the backfill), not a systemic recall gap.
- [x] 1.3 Document the audit findings (coverage gap vs. prompt/taxonomy recall vs. both) and confirm the scope of section 2 against them before writing any fix code. **Conclusion: coverage gap, not prompt/taxonomy recall.** The fixed pipeline (BATCH_SIZE 45->20, retry-once, timeout 300s->450s) took M1E from 6 entities (regressed) to 360 (vs. 97 originally) with only 1/121 batches hitting a network timeout and ~16/121 batches producing an unparseable LLM response (a batch-level failure mode distinct from network timeout, still resulting in zero entities from that batch but not counted by `uncovered_chunk_ids` since the HTTP call itself succeeded) - not a single case found of the model failing to recognize an entity type it should have. M2E's audit was not separately re-run (its 25-entity extraction predates the concurrency bug entirely, from an earlier session before full-document-scale ingestion was ever exercised) - out of scope to re-litigate here.

## 2. Entity extraction coverage fix (scope confirmed by section 1)

- [x] 2.1 Add a coverage-check helper that reports which chunks were not covered by any successful extraction batch for a document. Implemented as `ExtractionResult.uncovered_chunk_ids`, returned from `extract_entities_for_document`.
- [x] 2.2 Add retry-once-on-failure for a failed extraction batch in `extract_entities_for_document`, before its chunks are counted as uncovered.
- [x] 2.3 If the audit found a genuine prompt/taxonomy recall problem (not just coverage), adjust `_SYSTEM_PROMPT`/`CURATED_ENTITY_TYPES` in `entity_extractor.py` accordingly - skip this task if the audit found coverage was the sole cause. **Skipped** - audit (1.3) found coverage was the sole cause; no prompt/taxonomy change made. Noted as a follow-up, not fixed here: ~16/121 M1E batches got an HTTP-successful-but-unparseable-JSON response, which silently yields zero entities without being counted in `uncovered_chunk_ids` (that field only tracks network/timeout-level batch failures) - a secondary, smaller-impact gap worth a future retry-on-unparseable-response fix, out of scope for this change.
- [x] 2.4 Add/update tests in `tests/integration/test_entity_extraction.py` for retry behavior and coverage reporting.

## 3. Relationship storage

- [x] 3.1 Add `entity_relationships` table and schema migration in `src/database/entity_store.py` (`entity_id`, `related_entity_id`, `description`).
- [x] 3.2 Add `EntityStore.add_relationship(...)` and `EntityStore.get_relationships(entity_id)` (checking both `entity_id` and `related_entity_id` columns). Also added `list_all_relationships()` for the graph page, and taught `merge_entities` to reassign/drop relationship rows for merged entities.
- [x] 3.3 Unit tests for relationship storage and bidirectional retrieval.

## 4. Shared mention-context gathering

- [x] 4.1 Add a helper (e.g. in `src/pipeline/` or `src/wiki/`) that, given an entity's `EntityMention` list, fetches and returns the relevant chunk text, grouped/fetched per `document_id` via `VectorStore.get_chunks_by_document` (not per-mention), with a character/count budget to bound prompt size. Implemented as `src/pipeline/mention_context.py`'s `gather_mention_context`.
- [x] 4.2 Unit tests for the helper, including the multi-document and budget-capping cases.

## 5. Richer entity summaries

- [x] 5.1 Change `generate_entity_summary` in `src/wiki/summary.py` to take gathered mention context (from section 4) instead of only `entity.description`, and update its prompt accordingly.
- [x] 5.2 Update callers (`ingest.py`'s summarization step, `wiki/routes.py`'s on-demand fallback) to gather and pass mention context.
- [x] 5.3 Update/add tests for the new summary generation signature and behavior. Full suite (204 tests) passing.

## 6. Relationship extraction pipeline

- [x] 6.1 Add `src/pipeline/relationship_extractor.py`: given an entity, its gathered mention context (section 4), and the set of other known entities, ask the LLM for related entities (by name, matched back to `Entity` rows) and a short relationship description. Follow the existing `MAX_WORKERS`-low-concurrency pattern.
- [x] 6.2 Wire relationship extraction into ingestion (`ingest.py`), after entity extraction/dedup and summary generation, with the same "failure doesn't fail ingestion" behavior as other optional stages. Restructured `_prepare_wiki_data` so the (pre-existing) early-return for "no entities need summaries" no longer also skipped relationship extraction; relationships are generated once per entity (skipped if it already has at least one), mirroring the summary idempotency pattern.
- [x] 6.3 Add `scripts/extract_relationships.py` (modeled on `scripts/extract_entities.py`) to backfill relationships for already-ingested documents.
- [x] 6.4 Tests for relationship extraction, including the failure-doesn't-fail-ingestion and no-relationship-inferred cases. Full suite (212 tests) passing.

## 7. Wiki: relationships section on entity page

- [x] 7.1 Update `wiki_entity` route in `src/wiki/routes.py` to fetch and pass relationships to the template.
- [x] 7.2 Update `entity.html` to render a "Relationships" section (with the empty-state case handled). Also split the summary into paragraphs (`\n\n`-separated) since it can now be multi-paragraph.

## 8. Wiki: faction hub page

- [x] 8.1 Add a route (e.g. `/wiki/faction/{entity_id}`) or extend the existing entity route for faction-typed entities to include member entities (via "member of" relationships). Extended the existing `wiki_entity` route: for faction-typed entities, filters relationships whose description contains "member" (case-insensitive).
- [x] 8.2 Add `faction.html` template (or a conditional section in `entity.html`) listing members, with the no-members empty state handled. Used a conditional section in `entity.html`.

## 9. Wiki: location index page

- [x] 9.1 Add a `/wiki/locations` route listing all location-typed entities.
- [x] 9.2 Add `locations.html` template extending `base.html`, linking each location to its own entity page. Rendered as a `.entity-grid` of buttons (map-style) rather than the category page's descriptive bulleted list.
- [x] 9.3 Add navigation link to the location index from the sidebar/index page. Added a "Quick Links" section to the sidebar in `base.html`.

## 10. Wiki: relationship graph page

- [x] 10.1 Inspect current frontend JS conventions (`base.html` and existing templates) to decide the minimal client-side approach for a node-link graph. Found: no external JS libraries anywhere in the wiki, only one small inline `<script>` for search filtering. Went with zero client-side JS: node positions computed server-side (simple circular layout) and rendered as a static inline SVG.
- [x] 10.2 Add a `/wiki/graph` route returning all entities and relationships as graph data. Only entities that appear in at least one relationship are included as nodes, to avoid a wall of disconnected dots.
- [x] 10.3 Add `graph.html` template rendering the graph, with nodes linking to entity pages and an empty state when there are no relationships yet.

## 11. Backfill and verification

- [x] 11.1 Run the coverage fix, summary regeneration, and relationship backfill against the already-ingested M1E document (no full reprocess). Entity backfill: 6 -> 360 entities. Automated dedup dry-run found 18 candidate merge groups but ~40% were wrong (including a "safe-looking" group that actually conflated two distinct siblings) - applied only 6 high-confidence exact/unambiguous merges by hand, left the rest unmerged rather than trust the automated LLM-confirmation step blindly on this data (355 M1E entities remain). Summary + relationship generation launched detached (in progress as of this note) - deliberately bypassed `_prepare_wiki_data`'s automated dedup step for this run since dedup was already handled manually above.
- [x] 11.2 Run the full test suite; confirm no regressions. 225/225 passing.
- [x] 11.3 Live-verify in the running app: an entity page shows a longer summary and relationships, the faction hub lists members, the location index lists locations, and the graph page renders. Found and fixed a real deployment gap first: the backend/frontend had been running since before any of today's code changes (started 7/11, code changed 7/12-13) and were serving stale code - restarted both. After restart: Lady Justice's page shows a 2315-char multi-section summary (vs. the old 2-4 sentence blurb) and 18 relationships; the Guild faction page lists 12 members separately from its general relationships; `/wiki/locations` lists real locations; `/wiki/graph` renders 342 nodes / 1708 edges matching the DB exactly.
- [x] 11.4 Update the session log with audit findings, what was fixed, and results.

**Also found and fixed mid-backfill:** relationship extraction's candidate list was unbounded (every other entity in the store, ~379), causing a ~26% timeout rate on the real M1E dataset (vs ~1% for entity extraction). Added `_filter_candidates_by_context` (only ask about candidates actually named in the entity's own mention passages, same pattern as `entity_deduper.py`'s pre-filter) plus a `MAX_CANDIDATES=40` safety cap - timeout rate dropped to ~0% after the fix, and the restarted run actually found relationships (1708 total) vs. zero from the broken run.
