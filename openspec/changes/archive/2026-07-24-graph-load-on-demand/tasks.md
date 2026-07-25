## 1. Routes

- [x] 1.1 Rewrite `wiki_graph` (`src/wiki/routes.py`) to render `graph.html` with only the base sidebar context - no node/edge computation, no `entity_store.list_all_relationships()` call on the default path
- [x] 1.2 Add `GET /wiki/graph/data?entity_id=<id>`: look up the entity (404 via `HTTPException` if missing), gather its direct relationships via `entity_store.get_relationships`, lay out the focus entity centered with neighbors on a circle around it, return `{"nodes": [...], "edges": [...]}` in the shape the template expects
- [x] 1.3 Add `GET /wiki/graph/search?q=<text>`: wrap `entity_store.search_by_name`, return `[{"id": ..., "name": ...}, ...]`
- [x] 1.4 Add a "View in graph" link to `wiki_entity`'s template context/template pointing at `/wiki/graph?focus={{ entity.id }}`

## 2. Templates / JS

- [x] 2.1 `graph.html`: empty-by-default markup - search box + empty `<svg>`, no embedded full node/edge JSON blob
- [x] 2.2 Rewrite the inline JS: fetch-and-draw helper that takes a node/edge payload and (re)renders the SVG's nodes/edges/labels, wiring up click-to-fetch-neighborhood (replacing the previous set) and click-label-to-navigate as before
- [x] 2.3 Search box: debounce-free simple `input` handler hitting `/wiki/graph/search`, drawing the first/only good match's neighborhood (or showing a small pickable list if the query is ambiguous - keep this simple, single-best-match is enough for a first version)
- [x] 2.4 On page load, read `?focus=<id>` from `location.search` and if present fetch+draw that entity's neighborhood immediately
- [x] 2.5 Keep pan (pointer drag) and zoom (wheel) `viewBox` logic working against whatever is currently drawn
- [x] 2.6 `entity.html`: render the new "View in graph" link

## 3. Tests

- [x] 3.1 Update `test_wiki_graph_page_shows_related_entities` (`tests/integration/test_wiki.py`) to assert against `/wiki/graph/data?entity_id=<id>` instead of the bare page
- [x] 3.2 Re-scope `test_wiki_graph_page_empty_state` to the true-zero-relationships-in-the-DB case if that's still a distinct, meaningful state; add a new test asserting the bare `GET /wiki/graph` page has no node/edge markup by default even when relationships exist
- [x] 3.3 Leave `test_wiki_sidebar_links_to_graph_page` unmodified - the `/wiki/graph` link itself doesn't change
- [x] 3.4 New test: `/wiki/graph/data` for a known entity returns that entity plus its direct neighbors, and excludes entities it isn't directly related to
- [x] 3.5 New test: `/wiki/graph/data` for an unknown entity id returns 404
- [x] 3.6 New test: `/wiki/graph/search` returns matching entities by substring, case-insensitively
- [x] 3.7 New test: `wiki_entity` page includes a "View in graph" link with the right href

## 4. Manual verification

- [x] 4.1 Copy the real `data_storage/buddharauer.db` into the worktree, start the app, confirm bare `GET /wiki/graph` renders empty/searchable
- [x] 4.2 Search for a real entity name, confirm its neighborhood loads and draws (verified via `/wiki/graph/search` + `/wiki/graph/data` directly against the real DB - see design notes/report; full browser click-through not exercised, JS syntax-checked with `node --check` instead)
- [x] 4.3 Click a second node in the drawn neighborhood, confirm the view replaces with that node's neighborhood (verified the underlying `/wiki/graph/data` call the click handler makes returns a correctly re-centered neighborhood for a different entity id; not exercised via an actual browser click)
- [x] 4.4 Visit a wiki entity page, follow "View in graph", confirm the graph page loads already focused on that entity (verified the link's href and that the graph shell renders correctly regardless of `?focus=`, since focus is read client-side)
