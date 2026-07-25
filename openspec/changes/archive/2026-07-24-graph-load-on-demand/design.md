## Context

`/wiki/graph` (`src/wiki/routes.py:wiki_graph`) currently lays every entity with >=1 relationship out on a single circle (`center=300, radius=250`, positions computed by `math.cos`/`math.sin` over index/count) and draws a straight edge for every relationship. At the real current scale (~900 such entities, ~4,000 relationships) this is illegible - reviewed live by the user and judged "a design problem, not a tech problem" even though the underlying relationship data is sound. This was explicitly flagged as an unresolved Open Question in the prior change (`openspec/changes/archive/2026-07-17-interactive-graph-and-merge-tools/design.md`), which added pan/zoom/click-to-focus/search on top of the same full-graph render but didn't fix the root density problem.

Two directions were discussed there: (1) server-side force-directed layout, (2) don't render the full graph by default - load a small neighborhood on demand. This change builds (2), independently of a sibling change building (1) on another branch. The two are not compared or combined in this codebase; whoever reviews both later does that comparison.

## Goals / Non-Goals

**Goals:**
- Make `/wiki/graph` usable for the actual observed use case - "find this entity, see what it connects to" - at any node/edge count, by only ever drawing a small, human-scale subgraph (one entity + its direct neighbors) at a time.
- Give a natural path into a specific entity's neighborhood from three places: a cold search, clicking around an already-drawn neighborhood, and a direct link from that entity's own wiki page.
- Keep the "no client-side library, no build step" convention the existing graph JS already follows.

**Non-Goals:**
- Any layout-quality improvement for large simultaneous node counts (force-directed or otherwise) - out of scope, that's the sibling change's job. This change's answer to "the graph is dense" is "stop drawing it all at once," not "lay it out better."
- Multi-hop (depth >1) neighborhood expansion, or any "load more" affordance beyond depth-1 - a single click already re-centers on a new node, which reaches further entities transitively one click at a time; a fancier progressive-expansion UI isn't needed for this to be usable.
- Any change to how relationships are stored, extracted, or deduplicated.

## Decisions

### 1. Two new small JSON endpoints, not one parameterized page

`GET /wiki/graph/data?entity_id=<id>` returns `{"nodes": [...], "edges": [...]}` - same shape the template already expects (`{id, name, x, y}` / `{source_id, target_id, x1, y1, x2, y2}`) - for the given entity plus its direct relationships (`EntityStore.get_relationships(entity_id)`, which already normalizes both sides and excludes suppressed rows). 404s via `HTTPException` if the entity doesn't exist, consistent with `wiki_entity`'s existing 404 behavior. Layout: focus entity at the SVG center, its neighbors spaced evenly around a fixed-radius circle (same `center`/`radius` constants as before, just now applied to a handful of nodes instead of ~900 - a small subgraph on a circle is already legible, so no new layout logic is needed here, matching the Non-Goals above).

`GET /wiki/graph/search?q=<text>` wraps the existing `EntityStore.search_by_name` (already used by the admin manual-merge picker) to return `[{id, name}, ...]` matches. Considered instead: ship the full ~900-entity `{id, name}` list once on page load and match client-side. Rejected - it reintroduces exactly the "send everything up front" cost this change is trying to remove, for no real benefit at this entity count (substring search server-side is a trivial `LIKE` query already implemented and tested).

### 2. Clicking a node replaces the drawn set, not merges into it

When a user clicks a node's circle in an already-drawn neighborhood, the newly-fetched neighborhood replaces the current nodes/edges rather than being unioned in.

Chosen because: it directly matches the stated usage pattern ("what does X connect to") - each click answers that question fresh for a new X, and the view stays a small, readable circle no matter how many nodes get visited in a session. It's also simpler: no de-duplication logic for nodes/edges appearing in both the old and new neighborhood, no re-layout question for a growing mixed set, and no unbounded growth back toward "the whole graph" after enough clicks (which merging would eventually recreate - the exact problem this change exists to avoid).

Rejected alternative - merge into the existing set: defensible if a user wants to build up a manually-curated local map of a few entities' combined neighborhoods, but that's a different feature (more like the admin merge-review UI's deliberate multi-step state) than "browse the graph." Worth reconsidering if user feedback specifically wants to compare two entities' neighborhoods side by side; not attempted here.

### 3. `?focus=<entity_id>` deep link from the entity page

`wiki_entity`'s template gains a "View in graph" link to `/wiki/graph?focus={{ entity.id }}`. The graph page's JS, on load, checks `location.search` for `focus` and if present immediately calls the same fetch-and-draw path a search match or node click would use - no separate server-side code path, `wiki_graph` itself stays a dumb HTML shell that doesn't need to know about `focus` at all (it's read client-side from `window.location`). This is the change's one explicit nice-to-have (per the task brief) but is cheap (one link, a few lines of JS) and directly serves the actual use case that motivated this change in the first place - going from "reading about an entity" to "seeing its neighborhood" - so it's included rather than deferred.

### 4. `wiki_graph` itself becomes a static shell

`wiki_graph` no longer touches `entity_store` at all for the default case - it just renders `graph.html` with the base sidebar context, same as any other near-empty wiki page. All the node/edge/positioning logic that used to live in the route moves into `wiki_graph_data`. This is a clean split (page renders shell + JS; JSON endpoint computes data) rather than keeping a "sometimes full-graph, sometimes empty" branch in one handler.

## Risks / Trade-offs

- **[Risk]** This is a real, user-facing breaking change: a bare `GET /wiki/graph` no longer shows anything by default, whereas before it showed the full graph (illegible as that was). Anyone relying on "just load the page and eyeball the whole graph" loses that entirely. → **Accepted deliberately**: the prior behavior was already judged unusable at real scale by the user; an empty, searchable start is the tradeoff being deliberately made here, not a bug. Flagged explicitly in this proposal's "Why"/"What Changes" per the task brief.
- **[Risk]** A user who doesn't know any entity name in advance and didn't arrive via a `?focus=` link has no way to "just browse" the graph anymore (no more incidental discovery from seeing the whole thing at once). → **Accepted**: the wiki's category pages and search already serve as the "browse by name" entry point; the graph page's job is narrowed to "explore relationships from a known starting point," which matches how the user actually used it in the live review that motivated this change.
- **[Risk]** Depth-1-only neighborhoods mean a node with very high degree (e.g. a major faction with hundreds of members) still renders a dense circle when clicked. → **Accepted for this change**: still bounded by that one node's actual relationship count rather than the whole graph, and is a much smaller, real subset problem; not solved here (no per-neighborhood layout improvements are in scope per Non-Goals).

## Migration Plan

No schema or data migration - purely route/template/JS changes reusing existing `EntityStore` read methods. Deploying this change is a simple code deploy; no backfill, no `data_storage/buddharauer.db` changes needed.

## Open Questions

- None blocking. Whether depth-1 neighborhoods should ever expand to depth-2 (a literal "expand further" button rather than replace-on-click) is left for future user feedback once this ships and gets used against the real dataset.
