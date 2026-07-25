## Why

The relationship graph is illegible at real scale: M1E + M2E now put ~900 nodes and ~4,000 edges on a single static circular layout with no way to pan, zoom, or focus on one entity's neighborhood - the user's word for it was "a clusterfuck." Separately, entity deduplication is CLI-only (`scripts/dedupe_entities.py --dry-run`, reviewed by eye, applied by re-running without the flag) with no way to review candidates, merge arbitrary entities, or undo a bad merge from the admin UI - a real gap, since an earlier unreviewed auto-dedup pass had a ~40% false-positive rate and merged entities that were not actually duplicates (see session 7 notes and `src/pipeline/ingest.py`'s `_prepare_wiki_data` docstring).

## What Changes

- Relationship graph page (`/wiki/graph`) gains vanilla-JS interactivity on top of the existing server-computed circular layout - no new client-side library or CDN dependency, consistent with the wiki's existing zero-JS-dependency approach:
  - Pan and zoom (via SVG `viewBox` manipulation).
  - Click a node to highlight it and its directly-connected neighbors, dimming everything else.
  - A name search box that highlights/focuses a matching node.
- New password-gated admin capability, entity merge review, added to the existing Admin page:
  - Runs the existing dedupe candidate-finder (`entity_deduper.find_duplicate_groups`) on demand and presents each candidate group for one-at-a-time approve / reject / skip, instead of blind bulk-apply.
  - Manual merge tool: pick any two arbitrary entities and merge them, independent of the automated dedupe pass.
  - Merge history + split/undo: merges are now recorded (not just applied destructively), so a specific merge can be reversed later. **BREAKING**: `EntityStore.merge_entities` no longer hard-deletes the merged-away entity rows or leaves no trace of what was merged - this changes the merge data model (see design.md for why undo is not feasible against the current delete-and-reassign implementation, and what changes to make it reversible).

## Capabilities

### New Capabilities
- `entity-merge-review`: reviewing automated dedupe candidates, manually merging arbitrary entities, and reversing (splitting/undoing) a previously-applied merge, from the admin UI.

### Modified Capabilities
- `wiki`: the Relationship Graph Page requirement changes from a static node-link view to an interactive one (pan/zoom, neighborhood focus, search).
- `admin-controls`: the Admin Endpoint Rate Limiting requirement's scope extends to cover the new merge-review endpoints alongside the existing auth/query/upload/service-control ones.

## Impact

- `src/wiki/routes.py`, `src/wiki/templates/graph.html` (+ new static JS): interactive graph rendering.
- `src/database/entity_store.py`: merge data model changes to support reversibility (new storage for merge history; `merge_entities` no longer irreversibly deletes rows).
- `src/pipeline/entity_deduper.py`: reused as-is for candidate-finding, invoked on demand from an admin endpoint rather than only from a CLI script.
- `src/api/routes/admin.py`, `src/api/schemas.py`: new endpoints for listing dedupe candidates, approving/rejecting a candidate group, manual merge, and split/undo.
- `src/frontend/app.py`: new Admin-page section for merge review, manual merge, and undo.
- `scripts/dedupe_entities.py`: unaffected/still usable as a CLI alternative, now backed by the same reversible merge path.
- Tests across `tests/` for the above.
