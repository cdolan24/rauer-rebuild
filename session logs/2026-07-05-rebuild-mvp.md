# Session Log: 2026-07-05 - Buddharauer MVP Rebuild

**Branch:** `rebuild-mvp`
**OpenSpec changes covered:** `rebuild-mvp` (archived `2026-07-06-rebuild-mvp`), `admin-gated-upload` (archived `2026-07-06-admin-gated-upload`)

## Summary

Rebuilt Buddharauer (Malifaux story-PDF RAG chatbot) from a curated reference bundle (`base/rebuild_reference_2026-07-05/`) into a working local-first system, driven end-to-end through OpenSpec (`openspec init` -> `/opsx:propose` -> implement -> verify -> `/opsx:archive`).

## What was built

- **Ingestion pipeline** (`src/pipeline/`, `src/database/`): PyMuPDF text extraction, paragraph/sentence-aware chunking with page metadata, concurrent Ollama embeddings (`nomic-embed-text`), ChromaDB vector store (cosine similarity), SQLite document registry.
- **RAG chat** (`src/rag/`): retrieve-then-generate flow (no multi-agent framework - explicit simplification vs. the old FastAgent-based reference architecture), citations attached from chunk metadata, "no information" fallback, multi-turn conversation history. Local model: `llama3.2` via Ollama.
- **Backend** (`src/api/`): FastAPI - chat, documents, search, health endpoints.
- **Frontend** (`src/frontend/`): Gradio - chat + document viewer, citation-to-page jump, document selector, PDF upload.
- **Data ingested:** both real story PDFs - `MalifauxStories_M1E_DRAFT_5.17.2023.pdf` (629 pages, 2396 chunks) and `MalifauxStories_M2E_DRAFT_5.17.2023.pdf` (850 pages, 3178 chunks); 5574 chunks total. `MalifauxStories_TEST.pdf` (byte-identical to M1E) intentionally left unprocessed.

## Key decisions (user-directed)

- Runtime LLM: local via Ollama only, no cloud calls at runtime (Claude Code is dev-tool only).
- MVP scope: full pipeline end-to-end in one OpenSpec change, not phased.
- Skip multi-agent orchestration (FastAgent-style) for MVP - single retrieve-then-generate flow is sufficient.
- Wiki generation (entity extraction -> auto-generated pages) explicitly deferred to a future change.
- Only ingest PDFs already in `data/`; hold off on additional sample data until asked.
- Admin-gated upload: simple shared password (not full user accounts), matching the current evaluation stage.

## Bugs found and fixed during manual/browser verification

1. **Similarity-score scale bug** (found via Playwright browser test, not caught by unit tests): `VectorStore.search` converted ChromaDB's L2 distance to a score via `1/(1+distance)`, which stayed near 0.003-0.005 even for genuinely relevant matches. `ChatEngine`'s default `min_score=0.05` was unreachable, so real questions silently hit the "no information" fallback. **Fix:** ChromaDB collection now created with `hnsw:space: cosine`; score = `1 - distance` (bounded cosine similarity, ~0.6-0.7 relevant vs ~0.45-0.5 irrelevant in practice). `min_score` made configurable (`rag.min_score`, default `0.55`). Unit tests passed throughout because they explicitly set `min_score=0.0` - the bug was only visible with the real backend config, which is why the browser verification step mattered.
2. **Frontend timeout / "looks disconnected"** (reported directly by user after using the deployed app): frontend's HTTP client had a 60s timeout while real Ollama responses regularly took 40-90s+, with no progress indicator in the UI. **Fix:** timeout raised to a configurable `frontend.request_timeout` (default 180s); added an immediate "_Thinking..._" placeholder message via a generator-based Gradio callback so the chat never appears frozen.
3. Along the way: `python src/frontend/app.py` failed with `ModuleNotFoundError: No module named 'src'` when run directly as a script (only its own directory lands on `sys.path`) - fixed with the same `sys.path` insertion pattern already used in `scripts/process_documents.py`.

## New capability added

- **`admin-gated-upload`** (OpenSpec change, archived): `POST /api/documents/upload` and the frontend upload widget now require a correct admin password (`config.yaml`'s `auth.admin_password`, compared with `hmac.compare_digest`). A missing/placeholder (`"changeme"`) password disables uploads entirely rather than silently allowing them. Verified in-browser: wrong password -> visible rejection message, no ingestion; correct password -> accepted and ingests.

## Verification performed

- 58 automated tests passing (`pytest tests/`), ~97-100% coverage on all backend/pipeline modules (frontend Gradio UI intentionally untested - no automated harness for it in this MVP).
- Manual browser verification via Playwright (installed as a dev-only tool for this purpose, not a project dependency): chat + citations + document-viewer jump-to-page, multi-document retrieval (single question citing both M1E and M2E), admin password gate accept/reject, "Thinking..." indicator and no-timeout confirmation.
- Full cold reboot test (both servers killed and restarted from scratch) at the end of this session - health check, document list, and a live chat question all confirmed working post-reboot.

## State at end of session

- Branch `rebuild-mvp` pushed to `origin` (commits `2a35933`, `152cae4`, plus this session-log commit).
- `openspec/specs/` holds the current baseline (4 capabilities: `document-ingestion`, `rag-chat`, `chat-api`, `chat-frontend`), kept in sync with both archived changes.
- Backend (`localhost:8000`) and frontend (`localhost:7860`) running locally with both PDFs ingested.
- `config.yaml` (gitignored) holds a local admin password (`malifaux-admin`) for testing; `config.example.yaml` documents the placeholder.

## Open items for next session

- `MalifauxStories_TEST.pdf` (duplicate of M1E) sits unprocessed in `data/` by design - fine to ignore or delete.
- Real wiki generation (entity extraction -> auto-generated character/location/item pages) is still future work, per earlier user direction.
- Chunking doesn't respect story boundaries in this multi-story anthology - an occasional chunk/citation can straddle two different stories (observed directly on M1E pages 31-32). Harmless for MVP; worth a look if citation precision becomes a priority.
- No protection on any endpoint other than upload (chat/search/document-read stay open) - acceptable for the current evaluation stage per design notes in `admin-gated-upload`.
