## 1. Schema migration

- [x] 1.1 Add `merged_into_id INTEGER` (nullable) to `entities` via an `ALTER TABLE` run at `EntityStore` init time, ignoring the error if the column already exists
- [x] 1.2 Add `original_entity_id INTEGER` (nullable) to `entity_mentions` the same way
- [x] 1.3 Add `original_entity_id INTEGER`, `original_related_entity_id INTEGER` (nullable), and `suppressed INTEGER NOT NULL DEFAULT 0` to `entity_relationships` the same way
- [x] 1.4 Add a new `dedupe_candidates` table (`id, keep_id, merge_ids` as JSON text, `status`, `created_at`) to the schema
- [x] 1.5 Verify the migration runs cleanly against the real, populated `data_storage/buddharauer.db` without wiping or reprocessing anything

## 2. EntityStore changes

- [x] 2.1 Update `list_all`/`list_by_document`/`list_by_type` to exclude rows with `merged_into_id IS NOT NULL`; leave `get(id)` unfiltered
- [x] 2.2 Rewrite `merge_entities` to soft-delete (set `merged_into_id`) instead of deleting rows, and to stamp `original_entity_id`/`original_related_entity_id` only where not already set (preserve true original across a merge chain)
- [x] 2.3 Change self-loop handling in `merge_entities` from `DELETE` to setting `suppressed = 1`, preserving original ids
- [x] 2.4 Update `get_relationships`/`list_all_relationships` to exclude `suppressed` rows
- [x] 2.5 Add `can_undo_merge(entity_id) -> bool`: true only if the entity is soft-deleted (`merged_into_id` set) and its surviving entity hasn't itself been merged into anything since
- [x] 2.6 Add `undo_merge(entity_id)`: restore the entity row, move its mentions/relationships back, un-suppress qualifying relationships, clear the surviving entity's cached summary; raise/return an error if `can_undo_merge` is false
- [x] 2.7 Add dedupe-candidate CRUD: `save_candidates(groups)` (clears existing pending rows first), `list_candidates(status=None)`, `update_candidate_status(id, status)`

## 3. Admin API endpoints

- [x] 3.1 `POST /admin/dedupe/scan`: run `find_duplicate_groups` against `entity_store.list_all()`, persist as pending candidates (admin-password-gated, rate-limited like existing admin endpoints)
- [x] 3.2 `GET /admin/dedupe/candidates`: list candidates (with entity names/descriptions resolved for display, not just ids)
- [x] 3.3 `POST /admin/dedupe/candidates/{id}/approve`: re-validate entities still exist/aren't already merged before merging; auto-reject with a reason if stale
- [x] 3.4 `POST /admin/dedupe/candidates/{id}/reject` and `/skip`
- [x] 3.5 `POST /admin/merge`: manual merge of two arbitrary entity ids, reusing the same merge path as candidate approval
- [x] 3.6 `GET /admin/merges/undoable`: list recent merges eligible for undo (per `can_undo_merge`)
- [x] 3.7 `POST /admin/merges/{entity_id}/undo`: call `undo_merge`, returning a clear error if not eligible
- [x] 3.8 Add/update Pydantic schemas in `src/api/schemas.py` for all of the above

## 4. Admin frontend UI

- [x] 4.1 New "Entity Merge Review" group on the `/admin` page (same visibility-gated pattern as the existing upload/db-browser/service-control groups)
- [x] 4.2 "Scan for duplicates" button + a one-candidate-at-a-time review widget (entity names/descriptions, Approve/Reject/Skip buttons)
- [x] 4.3 Manual merge form: pick two entities (search/dropdown), confirm, merge
- [x] 4.4 Undo list: show undoable merges with an Undo button per row, and a note that pre-existing merges (from before this change) can't be undone
- [x] 4.5 Wire `src/frontend/api_client.py` with client methods for the new endpoints

## 5. Interactive relationship graph

- [x] 5.1 Embed the existing server-computed node/edge data as a JSON blob in `graph.html` (no change to the circular layout algorithm itself)
- [x] 5.2 Add a `<script>` (co-located static file, no external library) implementing pan (pointer drag) and zoom (wheel) via `viewBox` updates
- [x] 5.3 Add click-to-focus-neighborhood: build an adjacency map from the embedded edge list, toggle highlight/dim classes on click
- [x] 5.4 Add a name search box that reuses the highlight/focus path
- [x] 5.5 Add the corresponding CSS for highlighted/dimmed states

## 6. Tests

- [x] 6.1 EntityStore: soft-delete filtering, merge provenance stamping (including a merge-of-a-merge case), suppressed self-loop handling, undo restoring mentions/relationships/entity row, undo refusal on an ambiguous chain
- [x] 6.2 Dedupe-candidate persistence and re-scan replacing stale pending rows
- [x] 6.3 Admin API endpoints: auth-gating, stale-candidate auto-rejection, manual merge, undo (success and refusal cases)
- [x] 6.4 Existing entity_deduper/ingest tests still pass unmodified (candidate-finding logic itself is unchanged)

## 7. Manual verification

- [x] 7.1 Run the migration against the real `data_storage/buddharauer.db` and confirm existing M1E/M2E entities/relationships still display correctly afterward
- [x] 7.2 Live-test: scan for duplicates, approve one, reject one, manually merge two unrelated-looking entities, then undo it and confirm the original data is back
  - Manual merge + undo: verified live in the browser against real data (Malifaux/Kelly Brumley), round-trip confirmed in the DB.
  - Scan for duplicates: found a real Gradio-under-load bug in the process - the scan runs many sequential Ollama calls, and holding a single Gradio click open for that whole duration corrupts the browser's live connection on this CPU-only local-inference environment (`Cannot read properties of null (reading 'props')`, root-caused via ~15 isolated repros). Fixed by decoupling: `scan_btn` now kicks off the scan in a background thread and returns immediately ("Scan started..."); a new "Check scan results" button (`check_scan_results` in `src/frontend/app.py`) does a fast, separate fetch of the persisted pending candidates. Verified live end-to-end: scan → check results → approve candidate 1782 (Molly/Molly, confirmed merged in the DB) → reject candidate 1783 (confirmed rejected, not merged) → advanced correctly to the next candidate.
- [x] 7.3 Live-test the graph page: pan, zoom, click a node to focus its neighborhood, search for a known entity by name
