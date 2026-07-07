# Session Log: 2026-07-07 - Entity Extraction, Wiki, PDF Citations

**Branch:** `main`
**OpenSpec change:** `entity-wiki-and-citations` (archived `2026-07-07-entity-wiki-and-citations`)

## Summary

Delivered the three capabilities the original project brief called for and the MVP had deferred: content categorization (named entity extraction), a browsable Fandom-wiki-style site, and citations that point at the real PDF page instead of the plain-text extract.

## What was built

- **Entity extraction** (`src/pipeline/entity_extractor.py`, `src/database/entity_store.py`): batched (not per-chunk) LLM calls identify characters/locations/factions/items per document; mention indexing is plain substring matching (no extra LLM cost). Stored in new `entities`/`entity_mentions` SQLite tables.
- **Entity-aware retrieval boost** (`src/rag/retriever.py`): a query naming a known entity gets chunks tagged with it boosted (+0.05 cosine score) over a widened candidate pool.
- **Wiki** (`src/wiki/`): FastAPI + Jinja2, served from the backend (port 8000, not the Gradio frontend) - category index, per-entity pages with an LLM-written summary and "Mentioned In" citations. Linked from the main chat page.
- **PDF-native citations**: `GET /api/documents/{id}/pdf` + `#page=N` convention, used by both chat citations and wiki pages, so a human clicks through to the real formatted page instead of the plain-text dump.

## A real failure, and the fix

First M1E extraction run died partway through: a batch's LLM call timed out (even at the already-raised 180s backend timeout), and since the code did all-batches-then-all-mentions, the whole run's mention indexing was lost, not just the failed batch. Fixed by wrapping the per-batch call in try/except - log and skip, keep going - with a regression test. Also cleaned up twice: the crashed run's orphaned entities (no mentions) had to be deleted before re-running, since extraction doesn't dedupe against existing DB rows across separate runs.

## Real-world extraction runtime, and cutting the fat

Initial batch size (12 chunks/call) meant ~200 calls for M1E alone at ~60-90s each - impractical. Also discovered mid-run that any single Bash/PowerShell tool call (including backgrounded ones) caps at 10 minutes and gets killed - a multi-hour job can't run as one tool call. Fixed by launching extraction as a fully detached OS process (`nohup ... & disown`, same pattern already used for the backend/frontend servers) and polling for completion via `Get-CimInstance`/`Get-Process` instead. Per user direction to stop over-verifying once the mechanism was proven: batch size raised to 25 then 45 (M2E) once M1E confirmed the approach works, and the final verification pass was one tight script instead of a multi-step tour.

## Verification (kept deliberately minimal, per user direction)

- 99/99 tests passing (one run, not repeated per phase).
- Real extraction: M1E 99 entities/3635 mentions, M2E 34 entities/1526 mentions (133/5161 total). Sample of M1E entities included rulebook credits/author names alongside real Malifaux characters - a known limitation of LLM-based extraction over front-matter, not a bug; wiki content is generated, not authoritative, same framing as the chat's own citations.
- One Playwright + direct script pass: wiki index and a real entity page (Lady Justice) render correctly; PDF citation link resolves (`200`, `application/pdf`); retrieval boost measurably raises scores (+0.05) on entity-tagged chunks for a real "Who is Lady Justice?" query against the real vector store.

## State at end of session

- Commit `ef18252` on `main` (pushed).
- Backend + frontend restarted with the new build, both documents still indexed.
- No active OpenSpec changes.

## Open items

- Same as previous logs (`TEST.pdf` duplicate unprocessed by design, chunking can straddle story boundaries).
- Entity extraction occasionally picks up non-diegetic names (book credits) as "characters" - not filtered; would need a smarter prompt or a manual review step if this becomes a real problem.
- Cross-document entity de-duplication (e.g. "Lady Justice" exists as separate rows for M1E and M2E) is explicitly out of scope for now, per design.md.
