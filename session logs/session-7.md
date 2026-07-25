# Session 7

**Branch:** `session-6` (continued - still not merged to `main`, per session 6's explicit hold)
**OpenSpec changes:** `wiki-depth-and-relationships` (implemented, not yet archived)

## What was asked

Before reprocessing M2E with the vision pipeline: try `qwen2.5vl` and compare it against `llava` (session 6 never pulled it), fix the M1E entity-extraction regression from session 6 (97 -> 6 entities), then reprocess M2E. Mid-session, the user added a substantial second ask: increase wiki usage by making entries far denser, giving factions/locations dedicated hub pages, surfacing entity-to-entity relationships (both per-page and as a graph), and auditing why some things that should be wikified are missing - all **before** M2E gets reprocessed.

## qwen2.5vl vs. llava

Pulling `qwen2.5vl:7b` required upgrading Ollama first (0.6.7 -> 0.31.2 via winget - the old version's manifest pull returned a 412 asking for a newer client). Compared both against M1E's cover page: `llava` mis-read the title as "Malaux" and hallucinated fake publishers ("Mile High Comics", "University of Denver"); `qwen2.5vl` correctly read "Malifaux" and real book section names ("Rising Powers", "Twisting Fates"), at roughly 2.1x the latency (127.8s vs 60.2s). User chose `qwen2.5vl:7b` for M2E based on this.

## Entity-extraction regression: root-caused and fixed

Confirmed via code review (not just log-reading) that a failed batch in `entity_extractor.py` was silently and permanently lost - `_call_batch` returned `None` on any `OllamaError`, with no retry, and the response-processing loop just skipped `None` entries. Fixed:
- `BATCH_SIZE` 45 -> 20 (smaller batches process faster, bounding worst-case queued wait time)
- retry-once on a failed batch before giving up
- `request_timeout` 300s -> 450s
- `extract_entities_for_document` now returns an `ExtractionResult(entity_count, uncovered_chunk_ids)` instead of a bare int, so a coverage gap is reportable rather than silently absorbed

Backfilled M1E's entities from scratch (cleared the regressed 6-entity set, reran `scripts/extract_entities.py`): **360 entities**, well above the original 97, with only 1/121 batches hitting a network timeout (recovered by retry). Spot-checked 3 sampled pages against the extracted set - only one minor miss ("Stalker 263"), consistent with the ~16/121 batches that got an HTTP-successful-but-unparseable-JSON response (a secondary failure mode, not counted in `uncovered_chunk_ids`, noted as a follow-up rather than fixed this session). **Conclusion: coverage gap, not prompt/taxonomy recall** - no changes made to the extraction prompt or taxonomy.

## wiki-depth-and-relationships: fully implemented

Proposed via OpenSpec (proposal/design/specs/tasks, all validated), then implemented end to end:
- **Richer summaries**: `generate_entity_summary` now takes real mention-context text (new `src/pipeline/mention_context.py` helper, capped at 25 mentions / 6000 chars, fetched once per document not per mention) instead of only the entity's one-sentence stored description - root cause of "only a paragraph" was that the old prompt had almost nothing to summarize from.
- **Relationships**: new `src/pipeline/relationship_extractor.py` - one LLM call per entity, asks which of a candidate set it relates to and how, matched back to real `Entity` rows by name. New `entity_relationships` table + `EntityStore.add_relationship`/`get_relationships`/`list_all_relationships`; `merge_entities` now reassigns/drops relationship rows for merged entities too. Surfaced as a "Relationships" section on every entity page, a faction "Members" list (filtered by "member" appearing in the relationship description), and a new `/wiki/graph` page (plain server-computed circular layout, static inline SVG, zero client-side JS - matches the existing wiki's total absence of JS libraries).
- **Location index**: new `/wiki/locations` page, map-style grid of location buttons, linked from a new sidebar "Quick Links" section.
- 225/225 tests passing throughout (added ~40 new tests across entity extraction, entity store, mention context, relationship extraction, and wiki routes).

## Two real problems found while backfilling M1E's wiki data for real

**The automated entity-dedup tool is unreliable on real data.** A dry run against M1E's 360 backfilled entities found 18 candidate merge groups; on inspection, ~40% were wrong - including one that looked like the safest merge in the list (5 "Ryle"/"Hoffman" name variants) but actually conflated two distinct brothers whose relative-age descriptions contradicted each other across batches. Other false positives: "Death" merged into "Breath" (unrelated events), "Deputy Portmanteau" (a law officer) merged into "Portmanteau" (literally a horse), "Ellsa" merged into "Stella" despite their own descriptions saying Stella helps Ellsa. Applied only the 6 clearly-correct merges (exact cross-document name matches, unambiguous same-surname pairs) by hand rather than trust the tool's output wholesale - flagged to the user rather than deciding unilaterally, since blind application would have silently corrupted real entities. M1E: 355 entities after the safe merges (from 360).

**Relationship extraction's candidate list wasn't capped**, unlike design.md's stated risk ("for very large stores this could be expensive") - it really was. Passing every other entity in the store (~379) as candidates in every single prompt pushed the timeout rate to ~26%, and the run that hit this also turned out to store zero relationships even on its successful calls. Fixed with `_filter_candidates_by_context` (only ask about candidates whose name actually appears in the entity's own mention passages - same cheap-prefilter-before-LLM-call pattern already used in `entity_deduper.py`) plus a `MAX_CANDIDATES=40` safety cap. Timeout rate dropped to ~0% after restarting; the fixed run found **1708 relationships across 379 entities**.

## A repeat of session 6's stale-process lesson

Live-verifying the new wiki pages against `http://localhost:8000` initially showed no relationships at all despite 1708 being in the database - the backend and frontend had been running since before *any* of this session's code changes (started 7/11, code changed 7/12-13) and were serving stale code from memory. Restarted both; relationships, the faction hub, the location index, and the graph page (342 nodes / 1708 edges, matching the DB exactly) all verified correctly afterward.

## Verification

225/225 tests passing. Live-verified against the restarted app: Lady Justice's entity page shows a 2315-character multi-section summary (vs. the old 2-4 sentence blurb) and 18 relationships; the Guild faction page lists 12 members separately from its general relationships list; `/wiki/locations` lists real locations; `/wiki/graph` renders correctly.

## State at end of session

- Still on `session-6` branch, still not merged to `main`.
- `wiki-depth-and-relationships` OpenSpec change fully implemented (all 33 tasks), not yet archived.
- M1E: 355 entities (deduped), all with generated summaries, 1708 relationships extracted.
- M2E: still on the original ~25-entity extraction from before this session's fixes - **not yet reprocessed**. This was the original ask and is next.
- The Governor-General's-mansion hand-merge item from session 6 was explicitly skipped this session - the specific duplicate no longer existed (M1E's entity set had been reduced to 6 by the regression, wiping it along with everything else); not re-checked after the backfill regenerated a fuller set.

## Open items carried forward

- **Reprocess M2E next** - with the fixed entity extraction and `qwen2.5vl:7b` for vision, now that the wiki-depth-and-relationships work is done.
- The ~16/121 "HTTP-succeeded-but-unparseable-JSON" batch failures in entity extraction aren't retried or counted as coverage gaps (only network-level failures are) - a real, smaller-impact gap worth a future fix.
- Only 6 of 18 dedup candidate groups were applied for M1E; the rest (mostly plausible-but-uncertain guesses, plus the tangled 5-entity Hoffman group) were left unmerged rather than risk further wrong merges. Worth a closer look later, ideally with a less error-prone dedup approach than short single-sentence descriptions can support.
- M2E's entities have not been backfilled with the new richer summaries/relationships treatment - only M1E was.
- Decide on merging `session-6` to `main` (still explicitly on hold).
