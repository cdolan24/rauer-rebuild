## Why

The MVP proved the RAG pipeline works, but content is still an undifferentiated pile of chunks - there's no notion of "this is about Lady Justice" versus "this is about the Guild." The project's original goal (per the top-level README) was always to "auto-generate a wiki based on tagged information," and citations currently point at a plain-text dump that's fine for the AI but ugly for a human clicking through. This change delivers all three, since the wiki depends on entity tagging, and both benefit from PDF-native citations.

## What Changes

- Extract and tag named entities (characters, locations, factions, items) per ingested document using the local LLM, and index which chunks/pages mention each one.
- Use that tagging to make retrieval more targeted: when a query names a known entity, chunks tagged with it are boosted alongside plain vector similarity.
- Generate a browsable, Fandom-wiki-style website (category index + per-entity pages with an LLM-written summary and citation list) from the tagged entities.
- Add a way to cite the actual PDF page directly (opens the real, formatted page in the browser's PDF viewer) instead of only the plain extracted text, for both chat citations and the wiki.

## Capabilities

### New Capabilities
- `entity-extraction`: LLM-driven entity identification per document, mention indexing across chunks, and storage of both.
- `wiki`: server-rendered wiki website (category index, per-entity pages, citations) generated from tagged entities.
- `pdf-citations`: endpoint to serve the raw PDF and a `#page=N` linking convention so citations can point at the real document instead of the plain-text extract.

### Modified Capabilities
- `rag-chat`: retrieval requirement gains an entity-aware boost when a query names a known entity.
- `chat-frontend`: citations (in chat) gain a link to the real PDF page alongside the existing plain-text jump.

## Impact

- **Code**: `src/pipeline/entity_extractor.py`, `src/database/entity_store.py` (new), `src/wiki/` (new, templates + FastAPI routes), `src/api/routes/documents.py` (new PDF-serving endpoint), `src/rag/retriever.py` (entity-aware boost), `src/frontend/app.py` (PDF link alongside citations).
- **Data**: new SQLite tables (`entities`, `entity_mentions`) in the existing `data_storage` database.
- **Dependency**: `jinja2` for wiki templates (FastAPI already depends on it transitively; pinning it directly since we're using it ourselves now).
- **Non-goals**: no cross-document entity de-duplication/merging (an entity extracted separately from M1E and M2E is treated as distinct for now); no image/page rendering - PDF citation reuses the browser's native PDF viewer via `#page=N`, not a custom renderer.
