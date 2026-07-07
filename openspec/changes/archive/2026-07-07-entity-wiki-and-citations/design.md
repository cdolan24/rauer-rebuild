## Context

The MVP (`rebuild-mvp`) ingests PDFs into undifferentiated chunks in a vector store; nothing distinguishes "content about Lady Justice" from any other chunk. The original project README named auto-generating a wiki from tagged entities as the long-term goal, explicitly deferred out of the MVP. This change builds that tagging layer and the two things it unlocks: a browsable wiki, and PDF-native citations that reuse the same underlying data.

## Goals / Non-Goals

**Goals:**
- Tag chunks with the named entities (characters/locations/factions/items) they mention, without a per-chunk LLM call (5574 chunks would mean 5574 calls - too slow/expensive).
- Use that tagging to sharpen retrieval when a query names a known entity.
- Generate a real, browsable wiki site a human can navigate without going through the chatbot.
- Let a human click through a citation to the actual PDF page, not just the plain-text extract.

**Non-Goals:**
- Cross-document entity merging/de-duplication (an entity found in both M1E and M2E is stored twice, once per document, for now).
- Custom PDF page rendering (screenshots/images) - relies on the browser's built-in PDF viewer and the standard `#page=N` URL fragment instead.
- Real-time wiki updates - regenerated per ingestion run, not live-recomputed per request beyond simple template rendering.

## Decisions

**1. Entity extraction runs per-document in batches of chunks, not per-chunk.**
One LLM call per ~10-15 chunks (grouped by original document order) asking for named entities mentioned in that batch, with type and a one-line description. This keeps the LLM call count for M1E+M2E (5574 chunks) in the low hundreds rather than thousands, matching the same "why we skipped per-chunk overhead" reasoning already used for chunking/embedding batching.

**2. Mention indexing is plain substring matching, not another LLM pass.**
Once an entity's canonical name is known, finding which chunks mention it is a case-insensitive substring search over existing chunk text - free, fast, and good enough for a first pass. Aliases/nicknames are out of scope (an entity like "Lady Justice" won't automatically catch "the Guild judge" elsewhere) - a known limitation, not a bug, and consistent with keeping this MVP-scoped.

**3. Storage: two new SQLite tables (`entities`, `entity_mentions`), not a change to the vector store.**
`entities(id, document_id, name, type, description)` and `entity_mentions(entity_id, chunk_id, document_id, page_start, page_end)`. Keeping this in SQLite (alongside the existing document registry and query log) rather than as vector-DB metadata keeps the vector store's job simple (semantic search) and makes wiki page generation - which needs to list "all mentions of X" - a plain SQL query instead of a full collection scan.

**4. Retrieval boost is a simple score bump, not a rewritten ranking algorithm.**
If the query text contains a known entity name (case-insensitive substring match, same mechanism as mention indexing), chunks tagged with that entity get a small additive boost to their cosine similarity score before top-k selection. This is intentionally simple - a real hybrid-search re-ranker is more machinery than this MVP needs.

**5. Wiki is server-rendered HTML via FastAPI + Jinja2, not a Gradio page.**
A "Fandom wiki style" reference site (category index, cross-links, a page per entity) is a poor fit for Gradio's component model, especially once there are dozens/hundreds of entities. FastAPI already exists as the backend; adding `Jinja2Templates` and a few new routes (`/wiki`, `/wiki/category/{type}`, `/wiki/entity/{id}`) is far simpler than trying to force this into `gr.Blocks.route()`. The Gradio frontend gets a plain link to it.

**6. PDF citations: serve the raw file, link with `#page=N`, no custom renderer.**
A new `GET /api/documents/{id}/pdf` endpoint returns the original PDF (`FileResponse`, path already tracked in the document registry). Citations link to `.../pdf#page=N`; every modern browser's built-in PDF viewer honors that fragment. This is far simpler than rendering pages as images ourselves, and gives a human the actual formatted page - fonts, layout, and all - instead of our plain-text extract.

## Risks / Trade-offs

- **[Risk]** Batch-level entity extraction may miss entities that only appear once in a batch the model doesn't flag, or hallucinate one that isn't really named → **Mitigation**: acceptable at MVP scope; wiki pages are generated content, not authoritative, same spirit as the chat's own "explanatory, not infallible" framing.
- **[Risk]** Substring mention-matching will both miss aliases and occasionally over-match common words used as names → **Mitigation**: documented as a known limitation; revisit with real NER tooling only if it proves to matter in practice.
- **[Risk]** Re-running entity extraction on already-ingested documents (M1E, M2E) means another pass of LLM calls, taking real time → **Mitigation**: batched (not per-chunk) keeps it to minutes, not the ~20 minute scale of the original embedding ingestion.
- **[Risk]** Two citation paths (plain-text jump, PDF link) could drift out of sync in the UI → **Mitigation**: both are derived from the same `page_start`/`page_end` citation data; no separate source of truth.
