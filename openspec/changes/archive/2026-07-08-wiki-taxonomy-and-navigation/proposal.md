## Why

Live use of the wiki surfaced three concrete problems. First, the wiki's top-nav "Chat" link is a relative `href="/"`, but the wiki is served by the backend (port 8000) while chat lives on the frontend (port 7860) - a genuinely different origin. Clicking it 404s. Second, every entity - fictional or not - renders as an identical bright-red button, which both looks flat and actively misleads: real people (game credits like "Nathan Caroland, Author and producer of the M1E Core") are tagged `character` and rendered identically to fictional cast like Seamus, with no visual or categorical distinction. Third, the wiki's 4-type taxonomy (character/faction/item/location) is too coarse for a wiki approaching 150 entities; a Malifaux wiki in particular has a lot of non-human cast (undead, constructs) lumped in with human characters. Finally, `/wiki` currently *is* the category index - there's no actual front door with orientation/stats before diving into a wall of entities.

## What Changes

- Fix the wiki-to-chat link to be an absolute URL pointing at the frontend's actual configured address, not a same-origin relative path.
- Expand the entity taxonomy with three new curated types - `real-person` (game credits/authors, explicitly separated from fictional characters), `creature` (non-human cast: undead, constructs, monsters), and `event` (significant in-world events) - used both by future extraction and a one-time reclassification pass over the current 133 entities.
- Add a bounded **dynamic tagging** mechanism: during reclassification, the model may propose a genuinely novel tag beyond the curated set, but a novel tag only survives (becomes a real, visible wiki category) if at least 3 entities land in it; otherwise those entities fall back to their original type. This lets the taxonomy grow organically without one-off noise categories.
- Give each entity type its own distinct, muted color treatment instead of one bright red for everything, and visually de-emphasize the `real-person` category (it's meta/credits content, not story content).
- Turn `/wiki` into an actual landing page: an intro/orientation section with wiki-wide stats (entity count, document count, category breakdown) above the category browsing, rather than being the category index itself.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `entity-extraction`: taxonomy expands from 4 fixed types to a curated set (character/faction/item/location/real-person/creature/event) plus a threshold-gated dynamic tag mechanism.
- `wiki`: category index becomes a true landing page (stats + orientation, category browsing moves down/stays but isn't the whole page); entity buttons get per-type color treatment instead of a single color; cross-origin navigation link to chat is fixed.

## Impact

- `src/pipeline/entity_extractor.py` (taxonomy in the live extraction prompt).
- `src/database/entity_store.py` (needs an update-type method for reclassification).
- A new one-off reclassification script (parallel to the existing `scripts/extract_entities.py` pattern), run once against the current 133 entities.
- `src/wiki/routes.py`, `src/wiki/templates/*.html` (landing page, per-type colors, link fix).
- `src/utils/config.py` / `config.yaml` (wiki needs to know the frontend's URL to build the absolute chat link).
