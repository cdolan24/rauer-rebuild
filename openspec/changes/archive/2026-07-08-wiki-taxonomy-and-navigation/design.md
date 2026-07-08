## Context

Three concrete problems, each confirmed directly rather than assumed:

1. **Broken cross-origin link.** `src/wiki/templates/base.html` has `<a href="/">Chat</a>` in the persistent top nav. The wiki is rendered by the FastAPI backend (port 8000); chat is a separate Gradio app (port 7860). `curl http://localhost:8000/` returns 404 - the backend has no root route. The link only ever "worked" by accident if someone was already on the frontend's origin.

2. **Flat, misleading visual treatment.** Every entity button uses the same `.wiki-btn` bright red regardless of type, and the taxonomy itself conflates categories: querying `entities WHERE type='character'` returns both `Nathan Caroland - Author and producer of the M1E Core` and `Seamus - a wealthy and charismatic individual who has discovered the secrets to raising the dead`, back to back. 111 of 133 entities are typed `character`; only 4/1/17 are `faction`/`item`/`location`.

3. **No landing page.** `GET /wiki` directly renders the category index (`index.html`) - there's no orientation, no stats, nothing that reads as a home page before the entity wall.

## Goals / Non-Goals

**Goals:**
- Fix the broken chat link with an absolute URL.
- Expand the taxonomy to `character`, `faction`, `item`, `location`, `real-person`, `creature`, `event`, plus a bounded mechanism for the model to propose further tags that earn their place through repetition.
- Reclassify the current 133 entities into the expanded taxonomy via a fast one-off pass (not full re-extraction).
- Give each type a distinct, tasteful color; de-emphasize `real-person` visually since it's meta content, not story content.
- Turn `/wiki` into an actual landing page with stats/orientation above category browsing.

**Non-Goals:**
- Not fixing cross-document entity fragmentation/deduplication (e.g. "Molly Squidpiddge" appearing as 3 separate rows) - a real, known issue (carried from session 2's open items), but a different problem from mis-categorization and out of scope here.
- Not re-running full entity extraction from source text - the reclassification pass works from each entity's existing name/description, which is sufficient to fix categorization without hours of re-processing.
- Not building a general user-facing taxonomy editor - new tags are proposed by the model during the reclassification pass and gated by a fixed threshold, not manually curated per-entity.

## Decisions

1. **Absolute chat link via a new `frontend.public_url` config value.** The backend has no way to know how a browser reaches the frontend today (`frontend.api_base_url` is the reverse - how the frontend reaches the backend). Add `frontend.public_url` (default `http://localhost:{frontend.port}` if unset), pass it into every wiki route's template context, and render `<a href="{{ frontend_url }}">Chat</a>` instead of the relative `href="/"`.

2. **Curated taxonomy + threshold-gated dynamic tags, applied via a one-off reclassification script, not live per-upload.** `entity_extractor.py`'s fixed type set grows from 4 to 7 curated types - this is what future document uploads use directly. The "propose a new tag" allowance is reserved for the one-off reclassification pass over *all* existing entities at once, because judging whether a novel tag deserves to exist requires seeing its frequency across the whole entity set - a single newly-uploaded document can't make that call in isolation. Concretely: for each of the 133 entities, ask the model to pick one of the 7 curated types OR propose a short novel kebab-case tag only if truly none fit; tally novel-tag frequency in Python afterward; any novel tag with fewer than 3 members reverts those entities to their pre-reclassification type. Runs concurrently (`ThreadPoolExecutor`, same pattern as `embeddings.py`/`entity_extractor.py`'s batch extraction) since it's ~133 small, independent LLM calls.

3. **`EntityStore.set_type()`** - straightforward companion to the existing `set_summary()`, needed for the reclassification script to persist results.

4. **Per-type button colors, not per-entity.** `.wiki-btn.type-<type>` CSS classes with a distinct color per curated type (kept intentionally muted/varied rather than one loud color for everything); `real-person` gets a deliberately desaturated/gray treatment to read as "meta content" rather than story cast. Any surviving dynamic tag gets a shared neutral fallback color rather than a bespoke one - there's no way to know its semantics ahead of time.

5. **Landing page = stats/orientation block added above the existing category browsing**, not a wholesale rewrite of `index.html`. Keeps the category tiles (now colored per type) but adds a header section with total entity count, document count, and a per-category breakdown before them. Drops the "first 5 entities per category" preview that's currently on the index - that content now belongs to the category pages, and removing it from the landing page is what actually makes it read as a front door rather than a truncated dump.

## Risks / Trade-offs

- [LLM reclassification isn't perfectly deterministic - a borderline entity might get typed differently on a re-run] → Acceptable for a one-time backfill; the script is safe to re-run since `set_type` is a plain overwrite, not additive.
- [Entity fragmentation/deduplication remains unfixed] → Explicitly out of scope; still tracked as an open item.
- [`frontend.public_url` assumes a single, fixed, browser-reachable address] → Fine for this local-first single-user app; would need revisiting for a real multi-host deployment.
