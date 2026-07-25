## Context

Two independent problems, bundled because both surfaced from the same conversation and touch adjacent wiki/admin code:

1. `/wiki/graph` (`src/wiki/routes.py:wiki_graph`) lays every entity with >=1 relationship out on a single circle and draws straight edges - fine at the tens-of-nodes scale it was built against, illegible at the ~900 nodes / ~4,000 edges M1E+M2E now produce.
2. Deduplication (`src/pipeline/entity_deduper.find_duplicate_groups`) is only reachable via `scripts/dedupe_entities.py --dry-run`, reviewed by eye, then applied by re-running without the flag. `EntityStore.merge_entities` (`src/database/entity_store.py`) is destructive: it reassigns `entity_mentions`/`entity_relationships` rows onto `keep_id`, drops any relationship that became a self-loop, deletes the merged-away `entities` rows outright, and clears `keep_id`'s cached summary. There is currently no record anywhere of what got merged into what.

The database now holds real, expensive-to-regenerate data (two fully reprocessed documents' worth of LLM-generated summaries and relationships - see session 7 and the 2026-07-17 recovery). No prior schema change in this codebase has been applied as an in-place migration; every past schema change was absorbed by wiping and fully reprocessing the database, which is documented as file-based `CREATE TABLE IF NOT EXISTS` with no migration path. That option is now unattractive given how much compute is sitting in the current database - this change needs its first real additive migration instead.

## Goals / Non-Goals

**Goals:**
- Make the relationship graph usable for "find this entity and see what it connects to," even at current and larger scale.
- Let an admin review dedupe candidates one at a time (approve/reject/skip) instead of trusting a bulk apply.
- Let an admin manually merge two arbitrary entities, and reverse (split back apart) a merge performed through either path, without losing the data needed to do so.
- Migrate the existing database in place - no wipe/reprocess required.

**Non-Goals:**
- A physics-based/force-directed graph layout. The user explicitly chose hand-rolled vanilla JS over vendoring a layout library; the circular layout's visual crowding is not being fixed, only navigated around (pan/zoom/focus/search).
- Multi-level undo. Splitting a merge that was itself built from an already-merged entity (a merge chain), or splitting after further merges have landed on the same `keep_id`, is out of scope - see Risks.
- Changing `scripts/dedupe_entities.py`'s CLI behavior - it keeps working, now backed by the same reversible merge path as the admin UI.

## Decisions

### 1. Reversible merges via soft-delete + provenance columns, not a separate merge-log table

Rejected approach: a side `entity_merge_log` table storing a snapshot of the merged entity, with `entity_mentions`/`entity_relationships` still hard-reassigned and hard-deleted as today. This loses the *self-loop relationships that get dropped* (a relationship that existed between two entities that are about to be merged becomes meaningless post-merge and is deleted) - if the merge turns out to be wrong, that relationship is unrecoverable, and a separate log table can't help because the row it would need to restore was never preserved in the first place.

Chosen approach - keep every row, mark provenance instead of deleting:
- `entities`: add nullable `merged_into_id INTEGER`. Merging sets this on the merged-away row instead of deleting it. All existing list queries (`list_all`, `list_by_document`, `list_by_type`) add `WHERE merged_into_id IS NULL`; `get(id)` stays unfiltered so history/undo can still look up a merged-away entity by id.
- `entity_mentions` and `entity_relationships`: add nullable `original_entity_id` (and, for relationships, `original_related_entity_id`) recording the pre-merge id(s) before reassignment. Only set on the row's first reassignment - a row is treated as reassigned if its `original_entity_id` is already `NULL`, so a mention that's part of a later, second merge keeps pointing back to its *original* (pre-any-merge) entity, not an intermediate one. This is what makes split possible: to undo, filter every mention/relationship whose original column equals the merged-away id and set the live column back.
- `entity_relationships`: add `suppressed INTEGER NOT NULL DEFAULT 0`. A relationship that becomes a self-loop after reassignment is marked suppressed (excluded from `get_relationships`/`list_all_relationships`/the graph) rather than deleted, with its original entity/related-entity ids preserved so a split can un-suppress it and restore both original ids.
- A merge also snapshots the merged-away entity's pre-merge `name`/`type`/`description`/`summary` onto its own (now soft-deleted) row - since those fields are never touched by the merge itself (only `entity_mentions`/`entity_relationships` get reassigned), the row already holds everything needed to restore it. No separate snapshot storage needed.
- Split/undo: given a merged-away `entity_id`, (1) clear its `merged_into_id`; (2) move every `entity_mentions`/`entity_relationships` row with `original_entity_id = entity_id` back (`entity_id = entity_id`, clear `original_entity_id`); same for `original_related_entity_id` on relationships; (3) un-suppress any relationship rows whose `original_entity_id` or `original_related_entity_id` is this entity and whose other original side isn't itself being split back at the same time (both sides restored → real relationship again, restore normally); (4) clear `keep_id`'s cached summary (its mention set just changed again).

Alternatives considered: hard-delete + full JSON snapshot table (rejected above, loses self-loop relationships); event-sourcing the whole entities table (far more change than this warrants for a single-admin local tool).

### 2. In-place migration, not a wipe/reprocess

`EntityStore.__init__` currently runs `CREATE TABLE IF NOT EXISTS` unconditionally. Add a small migration step run at the same point: for each new column, attempt `ALTER TABLE ... ADD COLUMN ...` and ignore the `sqlite3.OperationalError` if it already exists (SQLite has no portable `ADD COLUMN IF NOT EXISTS` on the version this project's tested against). This is the first schema migration in this codebase's history that isn't "wipe and reprocess" - worth calling out explicitly since it sets a precedent other sessions should follow rather than reaching for a wipe by default.

### 3. Dedupe candidates are persisted, not recomputed per click

`find_duplicate_groups` runs one LLM call per same-type candidate pair - too slow to redo on every admin button click. Add a new `dedupe_candidates` table (`id, keep_id, merge_ids (JSON), status ('pending'|'approved'|'rejected'|'skipped'), created_at`). An admin action ("Scan for duplicates") runs `find_duplicate_groups` once and inserts fresh `pending` rows (clearing any previous `pending` rows first, so re-scanning doesn't pile up stale duplicates of the same candidate group). Reviewing a group applies the merge (or rejects/skips) and updates its status in place - this makes review resumable across page loads/admin sessions, at the cost of one more small table.

### 3b. The "Scan for duplicates" click fires the scan in a background thread, not inline

Discovered during live verification: `find_duplicate_groups` makes many sequential Ollama calls, and this project's inference is local and CPU-only (see [[feedback_resumable_pipeline]] - the same fragility that motivates resumable pipeline design elsewhere). Holding a single Gradio click's response open for that whole duration - even just one Ollama call, even with `MAX_WORKERS=1` - reliably corrupted the browser's live connection to the Gradio 6.20 dev server on this machine: the click's own component updates (a `gr.Markdown` + two `gr.State`s) silently never applied, with a `Cannot read properties of null (reading 'props')` client-side error and no server-side exception. Root-caused via ~15 isolated repro apps: not data shape, not output ordering, not `gr.State`-vs-visible-component mixing, not generic timing (a pure `time.sleep` or CPU-only busy-loop of the same duration never reproduced it) - only an actual live Ollama round-trip during the held-open click did, every time.

Fix: `scan_btn` (`start_scan` in `src/frontend/app.py`) now spawns `client.scan_for_duplicates` in a `threading.Thread(daemon=True)` and returns immediately with "Scan started...". A separate "Check scan results" button (`check_scan_results`) does a fast `GET /admin/dedupe/candidates` (already existing, no LLM calls) to pull the persisted pending candidates once the admin believes the scan has finished. This sidesteps the failure mode regardless of its exact mechanism, and is arguably better UX for a long-running action anyway.

If a future change adds another admin action that blocks on a real Ollama call from a single Gradio event, expect the same failure and apply the same fire-and-forget-plus-poll pattern preemptively rather than rediscovering this.

### 4. Graph interactivity is inline vanilla JS against a JSON payload embedded in the page

`wiki_graph` keeps computing the same circular-layout node/edge positions server-side (no change to the layout algorithm - see Non-Goals). The template additionally embeds the node/edge list as a `<script type="application/json">` blob; a plain `<script>` (no library, no build step, consistent with the rest of the wiki) reads it to:
- build an adjacency map for neighborhood highlighting on node click,
- implement pan (pointer drag) and zoom (wheel) by rewriting the `<svg>`'s `viewBox` attribute,
- implement the search box by substring-matching node names and re-using the same highlight/focus path as a click.

Alternative considered: compute a force-directed layout server-side in Python (no new runtime dependency, just different Python code). Rejected for this change - it's a real option but it's a layout-quality improvement orthogonal to interactivity, and the user's ask was specifically to avoid the heavier lift right now; worth a future change if navigation alone doesn't prove sufficient.

## Risks / Trade-offs

- **[Risk]** The circular layout stays visually dense even with interactivity - pan/zoom/focus makes it *navigable*, not visually clean. → **Mitigation**: the actual use case ("what does this entity connect to") is served by search + click-to-focus regardless of overall layout density; revisit a real layout algorithm later if this proves insufficient.
- **[Risk]** Undo only supports one level cleanly. If entity A merges into B, then B (carrying A's reassigned rows, now with `original_entity_id = A`) merges into C, splitting A back out of C is ambiguous - A's rows are indistinguishable from B's own original rows once both are living under C. → **Mitigation**: split is only offered in the UI for a merge whose `keep_id` has not itself been merged into anything else since; the merge-history view flags this rather than silently producing a bad split.
- **[Risk]** `dedupe_candidates` rows can go stale if an entity they reference gets manually merged (via the arbitrary-merge tool) before the candidate is reviewed. → **Mitigation**: approving a candidate re-validates that `keep_id` and every `merge_id` still exist and are not already `merged_into_id`-set; a stale candidate is marked `rejected` automatically with an explanation rather than erroring.
- **[Risk]** The existing Direct Database Access admin capability can already bypass all of this (e.g. `DELETE FROM entities`) - this change doesn't add any new protection against that path. → **Accepted**: out of scope, unchanged from today; the SQL browser has always been "the admin password is the only trust boundary" by explicit prior design (see `admin.py`'s existing docstring).

## Migration Plan

1. Add the new columns/table via the `ALTER TABLE`-with-ignore pattern in `EntityStore.__init__`, run automatically the next time the app starts against the existing `data_storage/buddharauer.db` - no manual step, no data loss, no reprocessing.
2. Existing rows: all new columns default to `NULL`/`0`, meaning "not merged, not suppressed" - correctly describes every row that exists today, so no backfill needed.
3. No rollback path is provided for the schema change itself (columns are additive and harmless to leave in place); if this change needs to be reverted, the added columns can simply be ignored by reverted code.

## Open Questions

- Whether split/undo should be exposed for merges applied before this change shipped (i.e., the M1E dedup merges from session 7, which have no provenance data since they predate these columns) - resolved as: no, those merges are already irreversible (the rows are gone), and this only protects merges applied after this change ships. Worth a one-line note in the admin UI so it isn't a surprise.
- **Not resolved - carried forward to a future change.** After shipping pan/zoom/focus/search, the user reviewed `/wiki/graph` live and judged it "nearly illegible... a design problem, not a tech problem" at the real ~900-node/~4000-edge scale, even though the underlying relationship data itself is sound. This is exactly the risk this change's Decision 4 flagged and explicitly deferred ("revisit a real layout algorithm later if this proves insufficient") - it has now proven insufficient. Two candidate directions discussed, not yet chosen between: (1) replace the circular layout with a server-side force-directed one so connected clusters actually cluster; (2) don't render the full graph by default at all - load empty, seed via search/click, draw only the resulting neighborhood. Recommended starting with (2) as the cheaper fix that matches actual usage ("what does X connect to"), with (1) as a possible follow-up. No implementation attempted yet - explicitly saved for a future session/change.
