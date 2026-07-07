## 1. Entity storage

- [x] 1.1 Add `src/database/entity_store.py`: SQLite tables `entities(id, document_id, name, type, description)` and `entity_mentions(entity_id, chunk_id, document_id, page_start, page_end)`, with insert/list/get-by-document/get-mentions methods
- [x] 1.2 Unit tests for `EntityStore`: create, list by document, list by type, get mentions for an entity

## 2. Entity extraction pipeline

- [x] 2.1 Add `src/pipeline/entity_extractor.py`: batches a document's chunks (~10-15 at a time), asks the local chat model for named entities (name, type, description) mentioned in each batch, parses the response
- [x] 2.2 Add mention indexing: case-insensitive substring match of each entity's name against all of the document's chunks, recording matches into `entity_mentions`
- [x] 2.3 Wire extraction into `src/pipeline/ingest.py` so new ingestions run it automatically after embedding
- [x] 2.4 Add `scripts/extract_entities.py` to (re-)run extraction for already-ingested documents (needed for M1E/M2E, ingested before this change)
- [x] 2.5 Unit tests: batch grouping, parsing the model's entity-list response (including malformed/partial responses), mention-indexing correctness
- [x] 2.6 Integration test: extraction + mention indexing end-to-end against a small synthetic document with a fake LLM client

## 3. Entity-aware retrieval boost

- [x] 3.1 Update `src/rag/retriever.py` (or `chat_engine.py`) to check the query text for known entity names and boost matching chunks' scores
- [x] 3.2 Unit tests: query naming a known entity boosts tagged chunks; query with no known entity name is unaffected

## 4. PDF-native citations

- [x] 4.1 Add `GET /api/documents/{id}/pdf` in `src/api/routes/documents.py` (FileResponse from the registry's source path; 404 for unknown documents)
- [x] 4.2 Frontend: add a "View original PDF" link next to the citation viewer in `src/frontend/app.py`, built from the selected citation's document id + page
- [x] 4.3 Tests: PDF endpoint success/404 cases

## 5. Wiki website

- [x] 5.1 Add `jinja2` to dependencies; set up `Jinja2Templates` (in `src/wiki/routes.py`, self-contained rather than `main.py`, for module cohesion)
- [x] 5.2 Add `src/wiki/routes.py`: `GET /wiki` (category index), `GET /wiki/category/{type}`, `GET /wiki/entity/{id}`
- [x] 5.3 Add templates: base layout, index/category listing, entity page (summary + "Mentioned In" citations linking to the PDF endpoint)
- [x] 5.4 Add entity summary generation (one LLM call per entity, using its extracted description as grounding, not re-reading mention text) - cached on the entity row so it isn't regenerated per page view
- [x] 5.5 Link to `/wiki` from the Gradio frontend's main page
- [x] 5.6 Tests: index/category/entity routes render with expected content; unknown entity id returns 404

## 6. Run against real data & verify

- [x] 6.1 Run entity extraction against the already-ingested M1E and M2E documents (99 + 34 = 133 entities, 5161 mentions; hit and fixed a per-batch resilience gap along the way)
- [x] 6.2 Run full test suite, confirm all green (99/99)
- [x] 6.3 Manual/Playwright verification: wiki index and an entity page render with real data; citation PDF links open the correct page (200, application/pdf); a chat question naming a known entity ("Lady Justice") shows the retrieval boost taking effect (+0.05 on tagged chunks, confirmed via direct score comparison)
