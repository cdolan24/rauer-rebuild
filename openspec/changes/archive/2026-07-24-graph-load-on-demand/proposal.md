## Why

The interactive circular-layout graph shipped in `2026-07-17-interactive-graph-and-merge-tools` added pan/zoom/focus/search on top of a static full-graph render, but that change's own Open Questions flagged it as insufficient: reviewed live against the real ~900-entity/~4,000-relationship dataset, the user judged it "nearly illegible... a design problem, not a tech problem," even though the underlying relationship data is sound. Rendering every related entity on a single circle on every page load doesn't scale, no matter how good the pan/zoom/focus interactions on top of it are.

Two directions were identified as follow-ups: (1) a server-side force-directed layout so connected clusters visually cluster, or (2) stop rendering the full graph by default - load empty, seed a small subgraph via search or click. This change implements (2). A sibling change implements (1) independently on a different branch, for later comparison; the two are not combined here and this change does not depend on or reference that work beyond noting it as the alternative considered.

## What Changes

- **BREAKING**: `GET /wiki/graph` no longer renders the full entity/relationship graph on load. It now renders an (almost) empty page: a search box and an empty SVG canvas, with no nodes/edges drawn until the user searches for an entity, clicks a drawn node, or arrives via a `?focus=<entity_id>` deep link. This directly supersedes the "lay out every entity with >=1 relationship" behavior the prior change shipped.
- New JSON endpoint `GET /wiki/graph/data?entity_id=<id>`: returns the given entity plus its direct (depth-1) relationships as `{"nodes": [...], "edges": [...]}` in the same shape `graph.html` already consumes, laid out as a simple circle with the focus entity centered. 404s on an unknown/nonexistent entity id.
- New JSON endpoint `GET /wiki/graph/search?q=<text>`: case-insensitive substring match over entity names (reusing `EntityStore.search_by_name`), returning a small list of `{id, name}` matches for the graph page's search box to pick from - avoids shipping a ~900-row name index to the client just to support "find this one entity."
- `graph.html`'s JS is rewritten around fetch-and-draw: typing in the search box queries `/wiki/graph/search`, picking a match (or an exact single match) fetches `/wiki/graph/data` and draws that neighborhood; clicking a drawn node's circle fetches and draws *that* node's neighborhood, replacing the previously-drawn set (not merging - see design.md for why). Clicking a node's label still navigates to its wiki entity page, unchanged.
- `wiki_entity` gains a "View in graph" link to `/wiki/graph?focus=<entity_id>`; the graph page's JS reads `?focus=` on load and auto-fetches/draws that entity's neighborhood, giving a direct path from an entity page into its graph neighborhood without a cold search.
- Pan/zoom (`viewBox` manipulation) is unchanged and still applies to whatever small subgraph is currently drawn.

## Capabilities

### Modified Capabilities
- `wiki`: the Relationship Graph Page requirement changes from "render the full graph, then interact with it" to "render nothing by default, load a single entity's neighborhood on demand via search, click, or a focus deep-link."

## Impact

- `src/wiki/routes.py`: `wiki_graph` no longer computes/passes the full node/edge list; new `wiki_graph_data` and `wiki_graph_search` JSON endpoints; `wiki_entity` gains a "View in graph" link in its template context (just the href, no new server logic beyond the entity id already in scope).
- `src/wiki/templates/graph.html`: empty-by-default markup; JS rewritten to fetch-and-draw instead of operating on an embedded full dataset.
- `src/wiki/templates/entity.html`: one new link.
- `tests/integration/test_wiki.py`: `test_wiki_graph_page_shows_related_entities` no longer applies to a bare `GET /wiki/graph` (moved to hit `/wiki/graph/data`); `test_wiki_graph_page_empty_state` re-scoped to the true-zero-relationships case; new tests for the data/search endpoints and the default-empty page.
- No database/schema changes - reuses `EntityStore.get`, `EntityStore.get_relationships`, `EntityStore.search_by_name` as they already exist.
