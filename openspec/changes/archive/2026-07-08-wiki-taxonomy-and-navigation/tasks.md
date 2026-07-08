## 1. Fix the cross-origin chat link

- [x] 1.1 Add `frontend.public_url` to config (default `http://localhost:{frontend.port}` if unset), `Config`/`load_config`
- [x] 1.2 Pass `frontend_url` into every wiki route's template context (`wiki_index`, `wiki_category`, `wiki_entity`)
- [x] 1.3 Update `base.html`'s "Chat" link to use `{{ frontend_url }}` instead of relative `href="/"`
- [x] 1.4 Verify the link resolves correctly (not a 404) via Playwright

## 2. Expand the entity taxonomy

- [x] 2.1 Extend `_ENTITY_TYPES` and `_SYSTEM_PROMPT` in `src/pipeline/entity_extractor.py` to the curated set: character/faction/item/location/real-person/creature/event
- [x] 2.2 Add `EntityStore.set_type(entity_id, type_)`
- [x] 2.3 Unit tests: extraction accepts all 7 curated types; `set_type` persists and is retrievable

## 3. Reclassification pass

- [x] 3.1 Write a one-off reclassification script (parallel to `scripts/extract_entities.py`): for each existing entity, classify via a small LLM call into one of the 7 curated types or a proposed novel tag; run concurrently (`ThreadPoolExecutor`, same pattern as existing extraction code)
- [x] 3.2 Tally novel-tag frequency in Python; discard (revert to prior type) any novel tag with fewer than 3 members
- [x] 3.3 Persist results via `EntityStore.set_type`
- [x] 3.4 Run the script against the current 133 entities; spot-check that known credits (e.g. "Nathan Caroland") land in `real-person` and known fictional characters stay in `character`/move to `creature` as appropriate

## 4. Visual differentiation

- [x] 4.1 Add per-type color CSS classes to `base.html` (`.wiki-btn.type-character`, `.type-faction`, `.type-item`, `.type-location`, `.type-real-person` (muted), `.type-creature`, `.type-event`, plus a neutral fallback for any surviving dynamic tag)
- [x] 4.2 Apply the `type-{{ entity.type }}` class to entity buttons in `index.html`, `category.html`
- [x] 4.3 Verify visually via Playwright screenshot

## 5. Wiki landing page

- [x] 5.1 Compute total entity count, document count, and per-category breakdown in `wiki_index` (`src/wiki/routes.py`)
- [x] 5.2 Add a stats/orientation section to `index.html`, above the category browsing
- [x] 5.3 Remove the "first 5 entities per category" preview from the index (that content now lives on category pages only)
- [x] 5.4 Verify the landing page renders correctly via Playwright

## 6. Verify & ship

- [x] 6.1 Run full test suite, confirm green
- [x] 6.2 Restart backend + frontend
- [x] 6.3 Playwright pass: chat link resolves correctly, entity buttons show distinct colors per type, real-person entities visually de-emphasized, landing page shows stats above category browsing, reclassified data renders correctly (spot-check a known real-person and a known character)
- [ ] 6.4 Archive the OpenSpec change (sync specs first), commit and push to `session-4`
