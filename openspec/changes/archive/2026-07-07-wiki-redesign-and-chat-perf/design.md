## Context

The wiki (`src/wiki/`) currently renders a single centered column per page (`base.html` + `index.html`/`category.html`/`entity.html`), with entity/category links styled as buttons (added last change) but no persistent navigation, no search, and no structured summary on entity pages. At ~133 entities across 4 types this is already hard to scan; it won't hold up as more documents are ingested.

Chat "thinking" time was measured directly against the real Ollama install (`ollama ps` confirms `100% CPU`, no GPU): a minimal 33-token prompt took 0.82s of prompt evaluation, but a realistic RAG prompt (~1020 tokens: 5 retrieved chunks + system prompt) took 26.98s of prompt evaluation alone, out of 38.44s total. Generation itself (`eval_duration`) was 11.36s for a 156-token reply (~14 tok/s). The dominant cost is prompt evaluation over the retrieved-context tokens, which streaming (last change) cannot help with - streaming only starts once the model finishes evaluating the prompt and begins producing tokens.

The PDF endpoint (`GET /api/documents/{id}/pdf`, added in `entity-wiki-and-citations`) uses Starlette's `FileResponse` with a `filename=` argument, which defaults to `Content-Disposition: attachment` - forcing a download instead of the inline rendering the frontend's iframe viewer (added last change) needs.

## Goals / Non-Goals

**Goals:**
- Give the wiki Fandom/Wikipedia-style navigational structure: persistent sidebar, instant client-side search/filter, an infobox-style summary on entity pages, breadcrumbs.
- Serve PDFs inline so the iframe viewer actually displays them.
- Bound the chat-latency growth that comes specifically from ever-growing conversation history, without touching the per-turn retrieval richness (chunk count/size) the user already confirmed they want to keep.
- Document, in the spec, that multi-citation/explanatory answers are an intentional requirement.

**Non-Goals:**
- Not reducing `top_k` or `chunk_size` (the retrieval context that produces the "increased information" the user likes) - that's a real, direct trade-off against answer quality and is called out as an open question for the user, not decided here.
- Not switching to a smaller/faster/quantized model, or attempting GPU acceleration - both are viable levers but are hardware/model choices outside this change's scope; noted as open questions.
- Not building a full-text search backend (FTS5, external search service, etc.) - at ~133 entities, everything needed for search already lives in the page-rendered data; a backend index is unwarranted complexity right now.

## Decisions

1. **Two-column wiki layout.** `base.html` gets a persistent left sidebar (category list with counts, always visible, plus the search box) and a main content area on the right, replacing the current single centered column. This mirrors both Fandom (left sidebar with categories/navigation) and Wikipedia (left sidebar with navigation, though Wikipedia's is thinner) - a single sidebar area is a well-understood pattern, cheaper to implement than either site's more elaborate chrome, and directly solves "no persistent navigation."

2. **Client-side search, no backend endpoint.** The sidebar search box filters entity buttons already present in the DOM (index/category pages) via a small inline `<script>` (keydown/input listener, no framework), matching on visible text. Rationale: entity count is small (~133) and every page that would need search already has the full entity list server-rendered; a client-side filter is instant, adds zero new dependencies, and avoids designing a search endpoint/index for a dataset this size. Alternative considered: a `/wiki/search?q=` backend endpoint with SQL `LIKE` - rejected as unnecessary complexity for the current data volume; revisit if entity count grows by an order of magnitude.

3. **Infobox on entity pages.** A right-aligned summary box (Wikipedia/Fandom convention) showing type badge, mention count, and the distinct source documents the entity appears in. Our entity data model (name/type/summary/description) doesn't support a rich attribute table the way a game-wiki infobox usually does, so this is intentionally lightweight - it's a scannability aid, not an attempt to replicate Fandom's structured-attribute infoboxes.

4. **Breadcrumbs.** `Wiki Home > {Category} > {Entity}` trail added to category and entity page templates, reusing existing route paths - no new backend logic, template-only.

5. **Bounded conversation history, not bounded retrieval.** Add `rag.max_history_turns` (default 3) to config; `ChatEngine`/`build_messages` only include the last N turns instead of the full unbounded history. This is the one speed lever that doesn't cost per-turn answer richness - a fresh question or the first few turns of a conversation are completely unaffected (they already have little/no history), and it directly stops the linear growth problem for long-running conversations. `top_k`/`chunk_size` are deliberately left untouched pending the user's call on the speed-vs-richness trade-off (see Open Questions).

6. **PDF inline disposition.** `FileResponse(..., content_disposition_type="inline")` on `GET /api/documents/{id}/pdf`. One-line fix, already applied; formalized here as a spec requirement so it doesn't regress.

## Risks / Trade-offs

- [Bounding history to 3 turns could lose relevant earlier context in long conversations] → Acceptable for now: most conversations in this app are 1-3 turns; retrieval (which re-embeds the current question fresh every turn) is unaffected regardless of history length, so answers stay grounded even if the model loses track of very old chat turns.
- [Client-side search doesn't scale indefinitely] → Fine at current and near-term entity counts; flagged as a revisit trigger if entity count grows an order of magnitude.
- [The biggest speed lever - GPU acceleration or a smaller model - isn't addressed here] → Explicitly out of scope; requires a hardware/model-choice decision from the user, not a code change.

## Open Questions

- Does the user want `top_k`/`chunk_size` reduced to trade some answer richness for speed, given they specifically praised the current richness? (Recommendation: leave as-is; the history-bounding change already gives some relief without that cost.)
- Is a smaller/faster Ollama model (or GPU-backed Ollama) worth evaluating for chat generation, given this machine currently runs 100% on CPU?
