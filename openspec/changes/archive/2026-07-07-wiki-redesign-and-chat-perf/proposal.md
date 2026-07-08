## Why

User feedback after using the session-3 build surfaced three things worth addressing before the next round: the wiki's current layout (plain headings, no navigation aids) doesn't hold up as the entity count grows past a hundred; chat responses spend a long time "thinking" before the first token appears, which measurement traced to CPU-bound prompt evaluation over a large retrieval context, not something the streaming work from the last change could fix; and the PDF viewer was silently downloading files instead of displaying them inline, defeating the point of embedding it in the page. Separately, the user confirmed the richer, multi-citation answer style introduced by entity-aware retrieval is a feature worth keeping, not an accident - worth making explicit in the spec so future changes don't regress it while chasing speed.

## What Changes

- Redesign the wiki's visual/navigational structure, taking cues from Fandom-wiki and Wikipedia conventions: persistent sidebar/category navigation, a lightweight client-side search/filter box, an infobox-style summary panel on entity pages, and breadcrumb-style navigation back to the category/index.
- **Diagnosed and documented** the chat "thinking" latency: measured via raw Ollama timing (`prompt_eval_duration`) that a realistic RAG prompt (~1000 tokens of retrieved context) takes ~27s of prompt evaluation alone on this CPU-only Ollama install, before any tokens stream. This is orthogonal to the streaming work already shipped - streaming makes generation feel responsive once it starts, but does nothing for the time-to-first-token. Options to reduce it (smaller retrieved context, bounding resent conversation history, faster/smaller model) trade directly against answer richness/thoroughness, which the user separately confirmed is desirable - this proposal documents the finding and a bounded-history mitigation that doesn't reduce per-turn retrieval quality, and defers other, quality-affecting levers to an explicit user decision rather than applying them unilaterally.
- Fix the PDF endpoint to serve `Content-Disposition: inline` instead of the default `attachment`, so the frontend's iframe viewer displays PDFs directly instead of triggering a browser download. (Already implemented as an immediate bugfix; this proposal formalizes it in the spec.)
- Document the multi-citation, explanatory answer style as an explicit, intentional requirement so it isn't inadvertently narrowed while pursuing speed improvements.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `wiki`: navigation/layout requirements change from a flat link/button list to a structured, searchable layout (sidebar nav, search, infobox, breadcrumbs).
- `pdf-citations`: the raw PDF serving endpoint must set inline content disposition, not force a download.
- `rag-chat`: add a requirement bounding how much conversation history is resent per turn (a speed lever that doesn't reduce single-turn retrieval quality); make explicit that multi-source, explanatory answers are an intentional behavior, not incidental.

## Impact

- `src/wiki/templates/*.html`, `src/wiki/routes.py` (likely a new search endpoint or client-side index), possibly `src/wiki/` static assets (new CSS, maybe minimal JS for search/filter).
- `src/api/routes/documents.py` (PDF disposition fix - done).
- `src/rag/chat_engine.py`, `src/rag/conversation_store.py` (conversation history bounding).
- `config.yaml` / `config.example.yaml` (new config for history-turn cap, if applicable).
- No changes required to the streaming/citation-button/keybinding work from `chat-speed-and-ui-polish` - this builds on top of it.
